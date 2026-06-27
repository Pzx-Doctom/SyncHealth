"""用药管理 Agent - 药盒 OCR + 药品查询 + 相互作用检查 + OTC 推荐"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from app.agents.base import (
    get_llm,
    append_route,
    parse_json_response,
    extract_tool_calls_from_messages,
)
from app.core.state import AgentState
from app.tools.registry import get_tools_for_agent

logger = logging.getLogger(__name__)


MEDICATION_PROMPT = """你是 SyncHealth 的用药管理助手。你的职责是帮助用户安全合理地使用药品。

## 核心能力
1. 接收用户上传的药盒图片，通过 OCR 识别药品信息
2. 查询药品的用法用量、适应症、禁忌症
3. 检查多种药物之间的相互作用
4. 根据用户描述的症状推荐 OTC 非处方药
5. 创建用药提醒
6. 调用 search_nearby_medical 查找附近药店

## 工作流程
1. 如果用户上传了药盒图片，先调用 ocr_medicine_box 识别药品
2. 调用 lookup_drug_info 查询药品详细信息
3. 如果用户有多种药品，调用 check_drug_interaction 检查相互作用
4. 如果用户描述了症状询问用药，调用 search_otc_drugs 推荐 OTC 药品
5. 如需购买，调用 search_nearby_medical 查找附近药店
6. 可调用 create_medication_reminder 创建用药提醒

## 安全边界（严格遵守）
- ⚠️ 绝对不推荐处方药，只推荐 OTC 非处方药
- ⚠️ 必须提醒用户咨询医生或药师
- ⚠️ 发现严重药物相互作用立即标记警告
- ⚠️ 对过敏史要特别关注（从用户画像获取）
- ⚠️ 不做疾病诊断，只做用药参考建议

## 输出要求
- 药品信息要准确完整（名称、用法、注意事项）
- 相互作用风险要明确标注（⚠️ 高风险）
- OTC 推荐必须附带"请咨询药师"的提示
- 如需购药，提供附近药店信息
- 用药提醒创建后要确认

## 边界（不要做）
- 不推荐处方药
- 不做疾病诊断
- 不给生活方式建议（交给健康教练）
- 不解读体检报告（交给报告解读）

## 重新路由
如果分析后发现用户问题更适合其他 Agent 处理，在回复末尾添加：
[REROUTE] {{"target": "health_coach|report_interpreter", "reason": "原因"}}
否则不要添加此标记。"""


async def medication_node(state: AgentState) -> dict:
    """用药管理 Agent 节点"""
    llm = get_llm()
    tools = get_tools_for_agent("medication")

    context_parts = [f"## 用户问题\n{state['user_query']}"]

    if state.get("memory_context"):
        context_parts.append(f"## 长期记忆（含用药历史和过敏史）\n{state['memory_context']}")
    if state.get("health_context"):
        context_parts.append(f"## 健康数据\n{state['health_context']}")
    if state.get("triage_reasoning"):
        entities = state.get("extracted_entities", {})
        if entities.get("has_image"):
            context_parts.append("## 注意：用户上传了药盒图片，请使用 OCR 工具识别")
        if entities.get("medications"):
            context_parts.append(f"## 提及的药品\n{', '.join(entities['medications'])}")

    input_text = "\n\n".join(context_parts)

    try:
        agent = create_react_agent(llm, tools, prompt=MEDICATION_PROMPT)

        result = await agent.ainvoke({"messages": [HumanMessage(content=input_text)]})
        output = result["messages"][-1].content

        # 收集工具调用记录
        tool_call_records = extract_tool_calls_from_messages(
            result["messages"], agent_name="medication"
        )

        # 检查重新路由
        reroute = None
        if "[REROUTE]" in output:
            reroute_section = output[output.index("[REROUTE]")+9:]
            reroute = parse_json_response(reroute_section)
            output = output[:output.index("[REROUTE]")].strip()

        new_route = []
        if reroute:
            new_route = append_route(
                state, "medication", "triage", reroute.get("reason", "重新路由")
            )

        logger.info(f"用药管理完成，工具调用 {len(tool_call_records)} 次")

        return {
            "messages": [AIMessage(content=output)],
            "tool_calls": state.get("tool_calls", []) + tool_call_records,
            "final_response": output,
            "reroute_request": reroute,
            "agent_route": state.get("agent_route", []) + new_route,
        }

    except Exception as e:
        logger.error(f"用药管理执行失败: {e}")
        return {
            "error": f"用药管理失败: {e}",
            "final_response": f"抱歉，用药分析过程中出现问题: {e}",
            "tool_calls": state.get("tool_calls", []),
        }
