import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.database import get_db, async_session_factory
from app.models.ai import ChatMessage as ChatMessageModel, ChatSession
from app.models.user import User
from app.schemas.ai import ChatMessageIn, ChatMessageOut, ChatSessionOut, DifyReference
from app.services.ai.agent_runtime import run_chat, DEFAULT_SYSTEM_PROMPT
from app.services.ai.base import ChatMessage
from app.services.ai.context_builder import build_health_context
from app.services.ai.dify_retriever import format_dify_context, retrieve_from_dify, parse_dify_records
from app.services.ai.factory import get_provider

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat")
async def chat(
    data: ChatMessageIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_id, response_text, dify_refs = await run_chat(
        db, current_user.id, data.message, data.session_id, data.agent_id
    )
    return {
        "session_id": session_id,
        "response": response_text,
        "dify_references": dify_refs,
    }


@router.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket, token: str = ""):
    # Authenticate via query param
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            message = data.get("message", "")
            session_id = data.get("session_id")
            agent_id = data.get("agent_id")

            async with async_session_factory() as db:
                # Load/create session
                session = None
                if session_id:
                    session = await db.get(ChatSession, session_id)
                    if session and session.user_id != user_id:
                        session = None

                if not session:
                    session = ChatSession(user_id=user_id, agent_id=agent_id)
                    db.add(session)
                    await db.flush()

                # Build context
                health_context = await build_health_context(db, user_id, message)

                # Retrieve medical knowledge from Dify
                dify_records = await retrieve_from_dify(message)
                dify_context = format_dify_context(dify_records)
                dify_refs = parse_dify_records(dify_records)

                # History
                history_result = await db.execute(
                    select(ChatMessageModel)
                    .where(ChatMessageModel.session_id == session.id)
                    .order_by(ChatMessageModel.created_at.desc())
                    .limit(20)
                )
                history = list(reversed(history_result.scalars().all()))

                messages = [
                    ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT),
                    ChatMessage(role="system", content=f"User's Health Data:\n\n{health_context}"),
                ]
                if dify_context:
                    messages.append(ChatMessage(role="system", content=f"Medical Knowledge Reference:\n\n{dify_context}"))
                for h in history:
                    messages.append(ChatMessage(role=h.role, content=h.content))
                messages.append(ChatMessage(role="user", content=message))

                # Save user message
                user_msg = ChatMessageModel(
                    session_id=session.id, role="user", content=message,
                    health_context_snapshot=health_context,
                    dify_context_snapshot=dify_context or None,
                )
                db.add(user_msg)

                # Stream response
                provider = get_provider()
                full_response = ""
                try:
                    async for chunk in provider.stream_chat(messages):
                        full_response += chunk
                        await websocket.send_text(json.dumps({"type": "token", "content": chunk}))
                except Exception:
                    # Fallback to non-streaming
                    if not full_response:
                        full_response = await provider.chat(messages)
                        await websocket.send_text(json.dumps({"type": "token", "content": full_response}))

                # Save assistant message
                assistant_msg = ChatMessageModel(
                    session_id=session.id, role="assistant", content=full_response,
                )
                db.add(assistant_msg)

                session.last_message_at = datetime.now(timezone.utc)
                if not history:
                    session.title = message[:50]

                await db.commit()

                await websocket.send_text(json.dumps({
                    "type": "done",
                    "session_id": session.id,
                    "dify_references": dify_refs,
                }))

    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1011)


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.last_message_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        return []

    result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.created_at.asc())
    )
    msgs = result.scalars().all()
    out = []
    for m in msgs:
        refs = None
        # Only user messages have dify_context_snapshot; associate refs with
        # the *next* assistant message for display. But simpler: parse snapshot
        # on user messages so frontend can pair them.
        if m.dify_context_snapshot:
            refs = _parse_snapshot_to_refs(m.dify_context_snapshot)
        out.append(ChatMessageOut(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            dify_references=refs if m.role == "user" else None,
        ))
    return out


def _parse_snapshot_to_refs(snapshot: str) -> list[DifyReference]:
    """Best-effort parse of the Markdown-formatted dify_context_snapshot back into references."""
    import re
    refs = []
    # Pattern: ### [DocName] (relevance: 0.92)
    # Optional: > Keywords: kw1, kw2
    # Then content until next ### or end
    pattern = re.compile(
        r'###\s*\[([^\]]+)\](?:\s*\(relevance:\s*([\d.]+)\))?\s*\n'
        r'(?:>\s*Keywords:\s*(.+?)\n)?'
        r'([\s\S]*?)(?=\n###\s*\[|\Z)',
    )
    for match in pattern.finditer(snapshot):
        doc_name = match.group(1)
        score = float(match.group(2)) if match.group(2) else None
        keywords = [k.strip() for k in match.group(3).split(",")] if match.group(3) else []
        content = match.group(4).strip()
        if content:
            refs.append(DifyReference(
                document_name=doc_name,
                score=score,
                keywords=keywords,
                content=content[:200],
            ))
    return refs


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        return {"detail": "Not found"}

    # Delete messages first
    result = await db.execute(
        select(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
    )
    for msg in result.scalars().all():
        await db.delete(msg)

    await db.delete(session)
    return {"detail": "Deleted"}
