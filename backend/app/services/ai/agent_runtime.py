import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai import AIAgent, ChatMessage as ChatMessageModel, ChatSession
from app.services.ai.base import ChatMessage, GenerationConfig
from app.services.ai.context_builder import build_health_context
from app.services.ai.dify_retriever import format_dify_context, parse_dify_records, retrieve_from_dify
from app.services.ai.factory import get_ollama_provider
from app.services.ai.provider_fallback import chat_with_fallback

DEFAULT_SYSTEM_PROMPT = (
    "You are SyncHealth AI, a knowledgeable and friendly health assistant. "
    "You analyze the user's Apple Watch health data to provide insights, "
    "answer health-related questions, and suggest improvements. "
    "When medical knowledge references are provided, use them to give more "
    "accurate and professional answers, but always clearly distinguish between "
    "general medical knowledge and personalized health advice. "
    "Always be supportive and remind users to consult healthcare professionals "
    "for medical advice. Respond in the same language the user uses."
)


async def run_chat(
    db: AsyncSession,
    user_id: int,
    message: str,
    session_id: int | None = None,
    agent_id: int | None = None,
    model: str | None = None,
) -> tuple[int, str, list[dict]]:
    """Run a synchronous chat completion. Returns (session_id, response_text, dify_references)."""
    # Load or create session
    if session_id:
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            session = None

    if not session_id or not session:
        session = ChatSession(user_id=user_id, agent_id=agent_id)
        db.add(session)
        await db.flush()

    # Load agent system prompt
    system_prompt = DEFAULT_SYSTEM_PROMPT
    data_scope = None
    if agent_id:
        agent = await db.get(AIAgent, agent_id)
        if agent and agent.user_id == user_id:
            system_prompt = agent.system_prompt
            if agent.health_data_scope:
                data_scope = json.loads(agent.health_data_scope)

    # Build health context
    health_context = await build_health_context(db, user_id, message, data_scope)

    # Retrieve medical knowledge from Dify
    dify_records = await retrieve_from_dify(message)
    dify_context = format_dify_context(dify_records)
    dify_refs = parse_dify_records(dify_records)

    # Load conversation history
    history_result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session.id)
        .order_by(ChatMessageModel.created_at.desc())
        .limit(20)
    )
    history_msgs = list(reversed(history_result.scalars().all()))

    # Build message list for LLM
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="system", content=f"User's Health Data:\n\n{health_context}"),
    ]
    if dify_context:
        messages.append(ChatMessage(role="system", content=f"Medical Knowledge Reference:\n\n{dify_context}"))
    for h in history_msgs:
        messages.append(ChatMessage(role=h.role, content=h.content))
    messages.append(ChatMessage(role="user", content=message))

    # Save user message
    user_msg = ChatMessageModel(
        session_id=session.id,
        role="user",
        content=message,
        health_context_snapshot=health_context,
        dify_context_snapshot=dify_context or None,
    )
    db.add(user_msg)

    # Call LLM (主 provider + 自动 fallback；若指定了非默认 model 则直接用 Ollama)
    config = GenerationConfig(model=model) if model else None
    if model and model != settings.AI_MODEL:
        # 用户手动选择了 Ollama 模型，直接用 OllamaProvider
        ollama = get_ollama_provider()
        response_text = await ollama.chat(messages, config)
    else:
        response_text = await chat_with_fallback(messages, config)

    # Save assistant message
    assistant_msg = ChatMessageModel(
        session_id=session.id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_msg)

    # Update session
    session.last_message_at = datetime.now(timezone.utc)
    if len(history_msgs) == 0:
        session.title = message[:50]

    return session.id, response_text, dify_refs
