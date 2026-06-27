"""健康教练 Agent - 可穿戴数据洞察 + 生活方式建议 + 轻度症状分析"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from app.agents.base import (
    get_llm,
    safe_llm_call,
    append_route,
    parse_json_response,
    extract_tool_calls_from_messages,
)
from app.core.state import AgentState
from app.tools.registry import get_tools_for_agent

logger = logging.getLogger(__name__)


HEALTH_COACH_PROMPT = """你是 SyncHealth 的个性化健康教练。你的职责是基于用户的可穿戴数据和健康目标提供专业建议。

## 核心能力
1. 基于可穿戴数据（步数、心率、睡眠、活动能量等）提供生活方式建议
2. 睡眠优化、运动计划、饮食建议、压力管理指导
3. 轻度症状分析（如"最近老觉得累""经常头疼"）结合数据找原因
4. 健康目标设定与进度追踪
5. 体检/运动康复建议，并可调用 search_nearby_medical 推荐附近机构

## 工作流程
1. 先调用工具获取用户的近期可穿戴数据（心率趋势、睡眠分析、活动摘要等）
2. 分析数据中的异常模式和趋势
3. 结合用户健康画像和目标给出个性化建议
4. 如需就医/体检，主动调用 search_nearby_medical 推荐附近机构

## 输出要求
- 建议要具体、可量化、可执行（如"每天步行 8000 步"而非"多运动"）
- 结合用户的历史数据和趋势，给出有数据支撑的建议
- 使用鼓励性语言，正向引导
- 如果发现数据异常（如心率持续偏高、睡眠严重不足），明确提醒用户关注

## 边界（不要做）
- 不处理药品相关问题（交给用药 Agent）
- 不解读书面体检报告（交给报告解读 Agent）
- 不做药物推荐
- 不做疾病诊断，只做分析和建议

## 重新路由
如果分析后发现用户问题更适合其他 Agent 处理（如涉及用药），在回复末尾添加：
[REROUTE] {{"target": "medication", "reason": "原因"}}
否则不要添加此标记。"""


async def health_coach_node(state: AgentState) -> dict:
    """健康教练 Agent 节点"""
    llm = get_llm()
    tools = get_tools_for_agent("health_coach")

    # 构建上下文
    context_parts = [f"## 用户问题\n{state['user_query']}"]

    if state.get("health_context"):
        context_parts.append(f"## 健康数据（来自 SyncHealth）\n{state['health_context']}")
    if state.get("memory_context"):
        context_parts.append(f"## 长期记忆\n{state['memory_context']}")
    if state.get("triage_reasoning"):
        context_parts.append(f"## 分诊信息\n意图: {state.get('intent')}, 紧急度: {state.get('severity')}\n提取实体: {json.dumps(state.get('extracted_entities', {}), ensure_ascii=False)}")

    input_text = "\n\n".join(context_parts)

    # 创建 React Agent（LangGraph 1.x 推荐方式）
    try:
        agent = create_react_agent(llm, tools, prompt=HEALTH_COACH_PROMPT)

        result = await agent.ainvoke({"messages": [HumanMessage(content=input_text)]})
        output = result["messages"][-1].content

        # 收集工具调用记录
        tool_call_records = extract_tool_calls_from_messages(
            result["messages"], agent_name="health_coach"
        )

        # 检查是否需要重新路由
        reroute = None
        if "[REROUTE]" in output:
            # 提取 reroute 信息
            reroute_section = output[output.index("[REROUTE]")+9:]
            reroute = parse_json_response(reroute_section)
            # 从输出中移除 reroute 标记
            output = output[:output.index("[REROUTE]")].strip()

        # 追加路由
        new_route = []
        if reroute:
            new_route = append_route(
                state,
                from_agent="health_coach",
                to_agent="triage",
                reason=reroute.get("reason", "重新路由"),
            )

        logger.info(f"健康教练完成，工具调用 {len(tool_call_records)} 次")

        return {
            "messages": [AIMessage(content=output)],
            "tool_calls": state.get("tool_calls", []) + tool_call_records,
            "final_response": output,
            "reroute_request": reroute,
            "agent_route": state.get("agent_route", []) + new_route,
        }

    except Exception as e:
        logger.error(f"健康教练执行失败: {e}")
        return {
            "error": f"健康教练分析失败: {e}",
            "final_response": f"抱歉，分析过程中出现问题: {e}",
            "tool_calls": state.get("tool_calls", []),
        }
