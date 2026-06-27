"""WebSocket 多 Agent 流式聊天端点"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.core.state import make_initial_state
from app.core.graph import get_compiled_graph
from app.models.session import Session, Message
from app.schemas.chat import ChatRequest, WSEvent, DoneData, ErrorData
from app.memory.manager import memory_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket 多 Agent 流式聊天端点。

    协议：
    - 客户端发送: {"message": "...", "session_id": null, "images": []}
    - 服务端推送事件: token | agent_switch | tool_start | tool_result | memory_recall | done | error
    """
    await websocket.accept()
    logger.info("WebSocket 连接已建立")

    try:
        while True:
            # 接收客户端消息
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                request = ChatRequest(**data)
            except Exception as e:
                await _send_error(websocket, f"消息格式错误: {e}")
                continue

            # 处理对话
            await _handle_chat(websocket, request)

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}", exc_info=True)
        try:
            await _send_error(websocket, f"连接异常: {e}")
        except Exception:
            pass


async def _handle_chat(websocket: WebSocket, request: ChatRequest):
    """处理一轮对话"""
    user_id = "default_user"  # 注：实际从 JWT 获取

    try:
        # 1. 获取或创建会话
        session_id = await _ensure_session(user_id, request.session_id)

        # 2. 保存用户消息
        await _save_message(session_id, "user", request.message)

        # 3. 构建初始 State
        initial_state = make_initial_state(
            user_id=user_id,
            user_query=request.message,
            session_id=session_id,
        )

        # 4. 获取编译后的图
        graph = await get_compiled_graph()

        # 5. 流式执行 LangGraph，推送事件
        final_state = None
        config = {"configurable": {"thread_id": f"user_{user_id}_session_{session_id}"}}

        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
            await _process_stream_event(websocket, event)

            # 保存最终状态
            if isinstance(event, dict):
                for node_name, state_update in event.items():
                    if node_name == "finalize":
                        final_state = state_update

        # 6. 获取最终回复
        final_response = "（无响应）"
        if final_state and isinstance(final_state, dict):
            final_response = final_state.get("final_response", final_response)

        # 7. 保存 AI 消息
        message_id = await _save_message(
            session_id=session_id,
            role="assistant",
            content=final_response,
            agent_route=final_state.get("agent_route", []) if final_state else [],
            tool_calls=final_state.get("tool_calls", []) if final_state else [],
            memory_recalls=final_state.get("memory_recalls", []) if final_state else [],
        )

        # 8. 提取并存储长期记忆
        if request.enable_memory and final_state:
            await memory_manager.extract_and_store_events(
                user_id=user_id,
                user_query=request.message,
                ai_response=final_response,
                agent_route=final_state.get("agent_route", []),
                tool_calls=final_state.get("tool_calls", []),
            )

        # 9. 发送 done 事件
        done_data = DoneData(
            session_id=session_id,
            message_id=message_id,
            agent_route=final_state.get("agent_route", []) if final_state else [],
            tool_calls=final_state.get("tool_calls", []) if final_state else [],
            memory_recalls=final_state.get("memory_recalls", []) if final_state else [],
        )
        await _send_event(websocket, "done", data=done_data.model_dump())

    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        await _send_error(websocket, f"处理失败: {e}", recoverable=True)


async def _process_stream_event(websocket: WebSocket, event: dict):
    """处理 LangGraph 流式事件，转换为 WebSocket 事件推送"""
    if not isinstance(event, dict):
        return

    for node_name, state_update in event.items():
        if not isinstance(state_update, dict):
            continue

        # Agent 路由切换事件
        if "agent_route" in state_update:
            routes = state_update.get("agent_route", [])
            if routes:
                latest = routes[-1]
                await _send_event(websocket, "agent_switch", data={
                    "from_agent": latest.get("from_agent", ""),
                    "to_agent": latest.get("to_agent", ""),
                    "reason": latest.get("reason", ""),
                    "severity": state_update.get("severity", "normal"),
                })

        # 工具调用事件
        if "tool_calls" in state_update:
            new_tool_calls = state_update.get("tool_calls", [])
            # 推送新增的工具调用
            for tc in new_tool_calls:
                await _send_event(websocket, "tool_result", data={
                    "agent": tc.get("agent", ""),
                    "tool": tc.get("tool", ""),
                    "result": tc.get("result", "")[:500],
                    "duration_ms": tc.get("duration_ms", 0),
                    "status": tc.get("status", "success"),
                })

        # 记忆召回事件
        if "memory_recalls" in state_update and state_update["memory_recalls"]:
            recalls = state_update.get("memory_recalls", [])
            await _send_event(websocket, "memory_recall", data={
                "events": recalls,
                "similarity_score": recalls[0].get("similarity", 0) if recalls else 0,
            })

        # Triage 思考过程
        if node_name == "triage" and "triage_reasoning" in state_update:
            reasoning = state_update.get("triage_reasoning", "")
            if reasoning:
                await _send_event(websocket, "thinking", content=f"分诊分析: {reasoning}")

        # 最终回复（流式推送）
        if "final_response" in state_update and state_update["final_response"]:
            await _send_event(websocket, "token", content=state_update["final_response"])


async def _send_event(
    websocket: WebSocket,
    event_type: str,
    content: str = None,
    data: dict = None,
):
    """发送 WebSocket 事件"""
    event = WSEvent(
        type=event_type,
        content=content,
        data=data,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    await websocket.send_text(event.model_dump_json())


async def _send_error(websocket: WebSocket, message: str, recoverable: bool = False):
    """发送错误事件"""
    error_data = ErrorData(message=message, recoverable=recoverable)
    await _send_event(websocket, "error", data=error_data.model_dump())


async def _ensure_session(user_id: str, session_id: int = None) -> int:
    """获取或创建会话，返回 session_id"""
    from app.database import async_session_factory

    async with async_session_factory() as session:
        if session_id:
            result = await session.execute(
                select(Session).where(Session.id == session_id, Session.user_id == user_id)
            )
            if result.scalar_one_or_none():
                return session_id

        # 创建新会话
        new_session = Session(user_id=user_id, title="新对话")
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        return new_session.id


async def _save_message(
    session_id: int,
    role: str,
    content: str,
    agent_route: list = None,
    tool_calls: list = None,
    memory_recalls: list = None,
) -> int:
    """保存消息到数据库，返回 message_id"""
    from app.database import async_session_factory

    async with async_session_factory() as session:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            agent_route=agent_route or [],
            tool_calls=tool_calls or [],
            memory_recalls=memory_recalls or [],
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg.id
