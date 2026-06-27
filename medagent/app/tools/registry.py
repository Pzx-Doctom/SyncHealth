"""工具注册表 - Agent 与工具的分配映射"""
from app.tools.location import search_nearby_medical
from app.tools.health_data import (
    get_heart_rate_trend,
    get_sleep_analysis,
    get_activity_summary,
    get_health_score,
    get_workout_history,
    get_vital_signs,
)
from app.tools.medication import (
    lookup_drug_info,
    check_drug_interaction,
    search_otc_drugs,
    ocr_medicine_box,
    get_user_medications,
    create_medication_reminder,
)
from app.tools.report import (
    ocr_medical_report,
    lookup_lab_reference,
    get_historical_lab_values,
    explain_medical_term,
    get_health_events,
)
from app.tools.knowledge import (
    search_medical_knowledge,
    search_fitness_knowledge,
)


# ===== 所有可用工具的注册表 =====
ALL_TOOLS = {
    # 位置查询（共享）
    "search_nearby_medical": search_nearby_medical,

    # 健康数据（MCP）
    "get_heart_rate_trend": get_heart_rate_trend,
    "get_sleep_analysis": get_sleep_analysis,
    "get_activity_summary": get_activity_summary,
    "get_health_score": get_health_score,
    "get_workout_history": get_workout_history,
    "get_vital_signs": get_vital_signs,

    # 用药管理
    "lookup_drug_info": lookup_drug_info,
    "check_drug_interaction": check_drug_interaction,
    "search_otc_drugs": search_otc_drugs,
    "ocr_medicine_box": ocr_medicine_box,
    "get_user_medications": get_user_medications,
    "create_medication_reminder": create_medication_reminder,

    # 报告解读
    "ocr_medical_report": ocr_medical_report,
    "lookup_lab_reference": lookup_lab_reference,
    "get_historical_lab_values": get_historical_lab_values,
    "explain_medical_term": explain_medical_term,
    "get_health_events": get_health_events,

    # 知识检索（RAG）
    "search_medical_knowledge": search_medical_knowledge,
    "search_fitness_knowledge": search_fitness_knowledge,
}


# ===== 各 Agent 的工具分配 =====
AGENT_TOOLS = {
    # Triage 不使用工具（纯推理）
    "triage": [],

    # 健康教练：可穿戴数据 + 知识 + 位置
    "health_coach": [
        "get_activity_summary",
        "get_sleep_analysis",
        "get_heart_rate_trend",
        "get_health_score",
        "get_workout_history",
        "search_fitness_knowledge",
        "search_nearby_medical",
    ],

    # 报告解读：OCR + 指标 + 历史 + 位置
    "report_interpreter": [
        "ocr_medical_report",
        "lookup_lab_reference",
        "get_historical_lab_values",
        "explain_medical_term",
        "get_health_events",
        "search_medical_knowledge",
        "search_nearby_medical",
    ],

    # 用药管理：OCR + 药品查询 + 相互作用 + OTC + 位置
    "medication": [
        "ocr_medicine_box",
        "lookup_drug_info",
        "check_drug_interaction",
        "search_otc_drugs",
        "get_user_medications",
        "create_medication_reminder",
        "search_medical_knowledge",
        "search_nearby_medical",
    ],
}


def get_tools_for_agent(agent_name: str) -> list:
    """获取指定 Agent 的工具列表（返回 LangChain Tool 对象）"""
    tool_names = AGENT_TOOLS.get(agent_name, [])
    return [ALL_TOOLS[name] for name in tool_names if name in ALL_TOOLS]


def get_tool_by_name(tool_name: str):
    """按名称获取工具"""
    return ALL_TOOLS.get(tool_name)
