"""finalize 节点 - 最终输出整合"""
from datetime import datetime, timezone

from app.core.state import AgentState


async def finalize_node(state: AgentState) -> dict:
    """
    最终输出节点：
    1. 如果 needs_clarification → 输出追问
    2. 如果有 error → 输出错误信息
    3. 否则 → 输出 final_response（已由专家 Agent 设置）
    """
    # 错误优先
    if state.get("error"):
        return {"final_response": f"⚠️ 处理过程中出现错误：{state['error']}"}

    # 需要澄清
    if state.get("needs_clarification"):
        question = state.get("clarification_question", "能否提供更多信息？")
        return {"final_response": question}

    # 循环超限
    from app.config import settings
    if state.get("loop_count", 0) >= settings.MAX_LOOPS:
        return {
            "final_response": "抱歉，系统在处理您的请求时经历了多次路由仍未能得出结论。"
                              "请尝试更具体地描述您的需求，或稍后再试。"
        }

    # 正常输出
    response = state.get("final_response")
    if not response:
        response = "抱歉，我暂时无法处理您的请求，请稍后再试。"

    return {"final_response": response}
