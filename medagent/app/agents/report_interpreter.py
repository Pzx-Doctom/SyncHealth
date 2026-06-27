"""报告解读 Agent - OCR 体检报告 + 指标对比 + 趋势分析 + 就医建议"""
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


REPORT_INTERPRETER_PROMPT = """你是 SyncHealth 的医学报告解读助手。你的职责是帮助用户理解体检报告和化验单。

## 核心能力
1. 接收用户上传的体检报告图片，通过 OCR 提取指标数据
2. 逐项对比医学参考范围，标注异常指标
3. 结合 SyncHealth 历史数据做趋势分析（如：半年前血糖 5.1→现在 6.3）
4. 用通俗语言解释医学术语
5. 给出就医建议并调用 search_nearby_medical 推荐附近医院

## 工作流程
1. 如果用户上传了图片，先调用 ocr_medical_report 提取数据
2. 对每个指标调用 lookup_lab_reference 查询参考范围
3. 如有历史数据，调用 get_historical_lab_values 做趋势对比
4. 对医学术语调用 explain_medical_term 做通俗解释
5. 综合分析后给出解读和建议
6. 如需就医，调用 search_nearby_medical 推荐附近相关科室

## 输出要求
- 清晰列出每项指标的检测结果和是否正常
- 对异常指标用醒目标记（⚠️）并解释意义
- 结合历史数据说明趋势变化
- 给出明确的就医建议（如需）
- 不做诊断，只做解读和建议

## 边界（不要做）
- 不提供用药建议（交给用药 Agent）
- 不给生活方式建议（交给健康教练）
- 不做疾病诊断（只做解读+建议就医）

## 重新路由
如果分析后发现用户问题更适合其他 Agent 处理（如涉及用药），在回复末尾添加：
[REROUTE] {{"target": "medication", "reason": "原因"}}
否则不要添加此标记。"""


async def report_interpreter_node(state: AgentState) -> dict:
    """报告解读 Agent 节点"""
    llm = get_llm()
    tools = get_tools_for_agent("report_interpreter")

    context_parts = [f"## 用户问题\n{state['user_query']}"]

    if state.get("memory_context"):
        context_parts.append(f"## 长期记忆\n{state['memory_context']}")
    if state.get("triage_reasoning"):
        entities = state.get("extracted_entities", {})
        if entities.get("has_image"):
            context_parts.append("## 注意：用户上传了图片，请使用 OCR 工具识别")

    input_text = "\n\n".join(context_parts)

    try:
        agent = create_react_agent(llm, tools, prompt=REPORT_INTERPRETER_PROMPT)

        result = await agent.ainvoke({"messages": [HumanMessage(content=input_text)]})
        output = result["messages"][-1].content

        # 收集工具调用记录
        tool_call_records = extract_tool_calls_from_messages(
            result["messages"], agent_name="report_interpreter"
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
                state, "report_interpreter", "triage", reroute.get("reason", "重新路由")
            )

        logger.info(f"报告解读完成，工具调用 {len(tool_call_records)} 次")

        return {
            "messages": [AIMessage(content=output)],
            "tool_calls": state.get("tool_calls", []) + tool_call_records,
            "final_response": output,
            "reroute_request": reroute,
            "agent_route": state.get("agent_route", []) + new_route,
        }

    except Exception as e:
        logger.error(f"报告解读执行失败: {e}")
        return {
            "error": f"报告解读失败: {e}",
            "final_response": f"抱歉，报告解读过程中出现问题: {e}",
            "tool_calls": state.get("tool_calls", []),
        }
