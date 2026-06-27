"""会话管理 API"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.session import Session, Message
from app.schemas.chat import ChatHistoryItem, ChatHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.get("")
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """列出用户的会话"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == DEFAULT_USER_ID)
        .order_by(Session.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_session_messages(
    session_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的消息历史"""
    # 验证会话存在
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id)
        .limit(limit)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        messages=[
            ChatHistoryItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat() if m.created_at else "",
                agent_route=m.agent_route or [],
                tool_calls=m.tool_calls or [],
                current_agent=m.current_agent,
            )
            for m in messages
        ],
        total=len(messages),
    )


@router.delete("/{session_id}")
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """删除会话（级联删除消息）"""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.delete(session)
    await db.commit()
    return {"message": f"会话 {session_id} 已删除"}


@router.patch("/{session_id}/title")
async def update_session_title(
    session_id: int,
    title: str,
    db: AsyncSession = Depends(get_db),
):
    """更新会话标题"""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.title = title
    await db.commit()
    return {"message": "标题已更新", "title": title}
