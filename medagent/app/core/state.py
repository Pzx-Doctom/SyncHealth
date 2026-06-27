"""LangGraph AgentState 定义 - Agent 间通信的唯一媒介"""
from datetime import datetime
from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentRouteEvent(TypedDict):
    """Agent 路由流转事件"""
    from_agent: str       # START | triage | health_coach | ...
    to_agent: str
    reason: str
    timestamp: str        # ISO 8601


class ToolCallRecord(TypedDict):
    """工具调用记录（用于前端可视化）"""
    agent: str            # 调用方 Agent 名
    tool: str             # 工具名
    args: dict            # 调用参数
    result: str           # 工具返回结果（截断到 500 字符）
    status: str           # success | error | timeout
    duration_ms: int
    timestamp: str


class MemoryRecallEvent(TypedDict):
    """长期记忆召回记录"""
    summary: str
    event_type: str       # health_event | conversation | preference
    timestamp: str
    similarity: float


class AgentState(TypedDict):
    """LangGraph 共享状态 - 贯穿整个对话流程"""

    # ===== 消息历史（LangGraph 自动累加） =====
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # ===== 用户上下文 =====
    user_id: str
    user_query: str                    # 原始用户输入
    session_id: int                    # 会话 ID（medagent.db 中的会话）

    # ===== Triage 决策结果 =====
    intent: str                        # lifestyle | report | medication | emergency | clarify
    severity: str                      # normal | attention | emergency
    target_agent: str                  # health_coach | report_interpreter | medication
    triage_reasoning: str
    extracted_entities: dict           # 提取的实体（症状、药物名、指标等）
    needs_clarification: bool
    clarification_question: str

    # ===== 数据注入（context_injection 节点填充） =====
    health_context: str                # MCP 获取的 SyncHealth 健康数据
    memory_context: str                # 长期记忆召回内容
    knowledge_context: str             # RAG 医学知识

    # ===== 执行追踪 =====
    tool_calls: list[ToolCallRecord]   # 所有工具调用记录
    agent_route: list[AgentRouteEvent] # Agent 流转路径
    memory_recalls: list[MemoryRecallEvent]  # 记忆召回记录

    # ===== 循环控制 =====
    loop_count: int                    # 当前循环次数（防死循环）
    reroute_request: Optional[dict]    # Agent 请求重新路由: {target, reason, context}

    # ===== 最终输出 =====
    final_response: Optional[str]      # 最终给用户的回答
    error: Optional[str]               # 错误信息


def make_initial_state(user_id: str, user_query: str, session_id: int) -> AgentState:
    """创建初始 AgentState"""
    now = datetime.utcnow().isoformat()
    return AgentState(
        messages=[],
        user_id=user_id,
        user_query=user_query,
        session_id=session_id,
        intent="",
        severity="normal",
        target_agent="",
        triage_reasoning="",
        extracted_entities={},
        needs_clarification=False,
        clarification_question="",
        health_context="",
        memory_context="",
        knowledge_context="",
        tool_calls=[],
        agent_route=[],
        memory_recalls=[],
        loop_count=0,
        reroute_request=None,
        final_response=None,
        error=None,
    )
