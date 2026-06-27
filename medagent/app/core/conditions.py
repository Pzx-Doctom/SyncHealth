"""LangGraph 条件路由函数"""
from typing import Literal

from langgraph.graph import END

from app.config import settings
from app.core.state import AgentState


def route_after_triage(
    state: AgentState,
) -> Literal["health_coach", "report_interpreter", "medication", "emergency", "finalize"]:
    """
    Triage 之后的路由决策。

    优先级：
    1. severity == emergency  →  emergency（最高优先级，跳过所有专家）
    2. intent == clarify      →  finalize（信息不足，直接返回追问）
    3. 按 target_agent 路由到对应专家
    4. 兜底 → finalize
    """
    severity = state.get("severity", "normal")
    intent = state.get("intent", "")
    target = state.get("target_agent", "")

    # 紧急情况：直接跳到 Emergency Agent
    if severity == "emergency":
        return "emergency"

    # 需要澄清：返回给用户追问
    if intent == "clarify" or state.get("needs_clarification"):
        return "finalize"

    # 按目标 Agent 路由
    route_map = {
        "health_coach": "health_coach",
        "report_interpreter": "report_interpreter",
        "medication": "medication",
    }
    result = route_map.get(target)
    if result:
        return result

    # 兜底：路由到 finalize 输出 Triage 的追问
    return "finalize"


def check_reroute(
    state: AgentState,
) -> Literal["triage", "finalize"]:
    """
    专家 Agent 执行后的检查：是否需要重新路由回 Triage。

    - 如果有 reroute_request 且未超循环上限 → 回到 triage
    - 否则 → finalize
    """
    reroute = state.get("reroute_request")
    loop_count = state.get("loop_count", 0)
    max_loops = settings.MAX_LOOPS

    # 防止无限循环
    if reroute and loop_count < max_loops:
        return "triage"

    # 有错误也要终结
    if state.get("error"):
        return "finalize"

    return "finalize"


def check_loop_limit(state: AgentState) -> bool:
    """检查是否超过循环上限"""
    return state.get("loop_count", 0) >= settings.MAX_LOOPS
