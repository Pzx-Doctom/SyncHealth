"""紧急处置 Agent - 生命安全第一，立即就医建议"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agents.base import get_llm, safe_llm_call
from app.core.state import AgentState
from app.tools.registry import get_tool_by_name

logger = logging.getLogger(__name__)


EMERGENCY_PROMPT = """你是紧急健康情况处置助手。当前用户的症状被判定为紧急情况。

## 核心原则（绝对优先）
1. 生命安全第一
2. 第一句话必须是明确的就医建议
3. 明确告知用户何时必须立即就医或拨打 120
4. 提供等待就医期间的正确处置方法
5. 不做任何可能延误就医的引导

## 输出格式（严格遵循）
1. 【紧急提醒】用 ⚠️ 开头，明确告知危险性和就医必要性
2. 【立即行动】拨打 120 或立即前往急诊
3. 【等待期间处置】2-3 条简明的急救建议
4. 【危险信号】列出需要特别警惕的恶化征兆
5. 【附近急诊】如已获取，列出最近的急诊医院

## 注意
- 不要安慰用户说"可能没事"
- 不要建议自行用药
- 不要建议观察等待
- 如有实时生命体征数据，结合分析
"""


async def emergency_node(state: AgentState) -> dict:
    """紧急处置 Agent 节点 - 不循环，直接输出"""
    llm = get_llm()

    # 尝试获取附近急诊医院
    nearby_emergency = ""
    try:
        search_tool = get_tool_by_name("search_nearby_medical")
        if search_tool:
            result = await search_tool.ainvoke({
                "query": "急诊",
                "place_type": "hospital",
                "radius": 10000,
                "max_results": 3,
            })
            nearby_emergency = f"\n\n## 附近急诊医院（已查询）\n{result}"
    except Exception as e:
        logger.warning(f"紧急情况下查询附近医院失败: {e}")
        nearby_emergency = "\n\n（附近医院查询失败，请用户自行拨打 120 或前往最近急诊）"

    context_parts = [f"## 用户症状描述\n{state['user_query']}"]

    if state.get("health_context"):
        context_parts.append(f"## 实时生命体征\n{state['health_context']}")
    if state.get("triage_reasoning"):
        context_parts.append(f"## 分诊判定\n{state.get('triage_reasoning')}")

    input_text = "\n\n".join(context_parts) + nearby_emergency

    messages = [
        SystemMessage(content=EMERGENCY_PROMPT),
        HumanMessage(content=input_text),
    ]

    try:
        response = await safe_llm_call(llm, messages)
        output = response.content

        # 追加路由（emergency 是终点，不循环）
        new_route = [{
            "from_agent": "triage",
            "to_agent": "emergency",
            "reason": "紧急情况直接处置",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

        logger.warning(f"紧急处置触发: {state['user_query'][:50]}")

        return {
            "messages": [AIMessage(content=output)],
            "final_response": output,
            "agent_route": state.get("agent_route", []) + new_route,
            "severity": "emergency",
        }

    except Exception as e:
        logger.error(f"紧急处置失败: {e}")
        # 紧急情况下的兜底回复
        return {
            "final_response": (
                "⚠️ 紧急情况！请立即拨打 120 或前往最近的医院急诊！\n\n"
                "在等待救援期间：\n"
                "1. 保持冷静，不要惊慌\n"
                "2. 保持呼吸通畅，解开紧身衣物\n"
                "3. 如有意识，保持半卧位\n"
                "4. 不要自行驾车就医\n\n"
                "（系统处理出现异常，以上为通用急救建议）"
            ),
            "error": str(e),
        }
