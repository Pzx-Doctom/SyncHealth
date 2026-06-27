"""Triage Agent - 分诊路由入口（纯推理，不调用任何 Tool）"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agents.base import get_llm, safe_llm_call, parse_json_response, append_route, increment_loop
from app.core.state import AgentState

logger = logging.getLogger(__name__)


TRIAGE_SYSTEM_PROMPT = """你是 MedAgent Hub 的分诊路由专家。你的唯一职责是分析用户输入并做出路由决策，**绝不直接回答用户的健康问题**。

## 你的职责
1. 分析用户输入，理解其真实需求和意图
2. 评估紧急程度（normal / attention / emergency）
3. 决定由哪个专家 Agent 处理
4. 当信息不足时，生成澄清问题

## 路由规则

| 用户意图 | 关键特征/关键词 | 路由目标 (target_agent) | 紧急度 (severity) |
|---------|---------------|----------------------|------------------|
| 生活方式咨询 | 运动/睡眠/饮食/压力/减肥/步数/卡路里 | health_coach | normal |
| 轻度症状 | 头疼/疲劳/腰酸/偶尔不适（非急性，持续状态） | health_coach | attention |
| 报告上传 | 体检报告/化验单/检查结果/图片报告 | report_interpreter | normal |
| 用药咨询 | 药品用法/剂量/副作用/药盒/相互作用 | medication | normal |
| 症状+用药 | 症状描述 + 询问用药 | medication | attention |
| 紧急症状 | 剧烈胸痛/呼吸困难/意识模糊/严重出血/突发剧痛 | (emergency) | emergency |
| 信息不足 | 用户输入模糊（如"我不舒服"） | (clarify) | normal |

## 紧急度评估标准
- 🟢 normal：日常咨询、常规问题、报告解读、用药查询
- 🟡 attention：持续症状、指标异常但非急性、需要关注但非紧急
- 🔴 emergency：剧烈胸痛、呼吸困难、意识改变、严重出血、突发剧烈头痛

## 路由目标说明
- health_coach：健康教练 - 可穿戴数据分析、生活方式建议、轻度症状分析
- report_interpreter：报告解读 - OCR 体检报告、指标对比、就医建议
- medication：用药管理 - 药品查询、相互作用、OTC 推荐、用药提醒
- 当 severity=emergency 时，target_agent 留空，系统会自动路由到紧急处置

## 输出格式（必须严格 JSON）
{
  "intent": "lifestyle|symptom_mild|report|medication|emergency|clarify",
  "severity": "normal|attention|emergency",
  "target_agent": "health_coach|report_interpreter|medication",
  "reasoning": "简短的路由理由（一句话）",
  "extracted_entities": {
    "symptoms": [],
    "medications": [],
    "duration": "",
    "has_image": false
  },
  "needs_clarification": false,
  "clarification_question": ""
}

## 注意事项
- 当 severity=emergency 时，target_agent 设为空字符串 ""
- 当 needs_clarification=true 时，intent 设为 "clarify"，target_agent 设为空字符串 ""
- 不要编造用户没有提到的症状
- extracted_entities 只包含用户明确提到的内容"""


async def triage_node(state: AgentState) -> dict:
    """
    Triage Agent 节点：
    1. 接收用户输入 + 三种上下文
    2. LLM 分析意图、紧急度、路由目标
    3. 输出结构化 JSON 更新 State
    4. 记录 agent_route 流转
    """
    llm = get_llm()
    user_query = state["user_query"]

    # 构建上下文提示
    context_parts = []
    if state.get("health_context"):
        context_parts.append(f"## 用户健康数据（来自 SyncHealth）\n{state['health_context']}")
    if state.get("memory_context"):
        context_parts.append(f"## 用户长期记忆\n{state['memory_context']}")
    if state.get("knowledge_context"):
        context_parts.append(f"## 医学知识参考\n{state['knowledge_context']}")

    # 如果有 reroute 请求（循环回来的场景）
    reroute_info = ""
    if state.get("reroute_request"):
        reroute = state["reroute_request"]
        reroute_info = (
            f"\n\n## 重新路由请求\n"
            f"上一个 Agent ({reroute.get('from_agent', 'unknown')}) 请求重新路由\n"
            f"原因: {reroute.get('reason', '未知')}\n"
            f"携带上下文: {json.dumps(reroute.get('context', {}), ensure_ascii=False)}"
        )

    loop_info = f"\n当前路由轮次: {state.get('loop_count', 0)} / {state.get('MAX_LOOPS', 5)}"

    context_block = "\n\n".join(context_parts) + reroute_info + loop_info

    messages = [
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        SystemMessage(content=context_block),
        HumanMessage(content=user_query),
    ]

    # 调用 LLM（带重试）
    try:
        response = await safe_llm_call(llm, messages)
        raw_content = response.content
    except Exception as e:
        logger.error(f"Triage LLM 调用失败: {e}")
        return {
            "error": f"分诊分析失败: {e}",
            "final_response": "抱歉，系统暂时无法处理您的请求，请稍后再试。",
        }

    # 解析 JSON（带降级）
    triage_result = parse_json_response(
        raw_content,
        fallback={
            "intent": "lifestyle",
            "severity": "normal",
            "target_agent": "health_coach",
            "reasoning": "JSON 解析失败，降级路由到健康教练",
            "extracted_entities": {},
            "needs_clarification": False,
            "clarification_question": "",
        },
    )

    # 确保 emergency 优先级
    severity = triage_result.get("severity", "normal")
    intent = triage_result.get("intent", "lifestyle")
    target_agent = triage_result.get("target_agent", "health_coach")

    if severity == "emergency":
        target_agent = ""  # 紧急时清空，由路由函数处理

    if triage_result.get("needs_clarification"):
        intent = "clarify"
        target_agent = ""

    # 计算实际路由目标（用于显示和记录）
    if severity == "emergency":
        route_target = "emergency"
    elif triage_result.get("needs_clarification"):
        route_target = "finalize"
    else:
        route_target = target_agent or "finalize"

    # 记录 Triage 的系统消息
    system_msg = AIMessage(
        content=f"[Triage] 意图={intent}, 紧急度={severity}, "
                f"路由={route_target}, 理由={triage_result.get('reasoning', '')}"
    )

    # 追加路由事件
    from_agent = "START" if state.get("loop_count", 0) == 0 else \
        (state.get("agent_route", [{}])[-1].get("to_agent", "triage") if state.get("agent_route") else "START")
    new_route = append_route(
        state,
        from_agent=from_agent,
        to_agent=route_target,
        reason=triage_result.get("reasoning", ""),
    )

    logger.info(f"Triage 决策: intent={intent}, severity={severity}, target={target_agent}")

    return {
        "messages": [system_msg],
        "intent": intent,
        "severity": severity,
        "target_agent": target_agent,
        "triage_reasoning": triage_result.get("reasoning", ""),
        "extracted_entities": triage_result.get("extracted_entities", {}),
        "needs_clarification": triage_result.get("needs_clarification", False),
        "clarification_question": triage_result.get("clarification_question", ""),
        "agent_route": new_route,
        "loop_count": increment_loop(state),
        "reroute_request": None,  # 清除 reroute 请求
    }
