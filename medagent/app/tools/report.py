"""报告解读工具 - OCR、指标参考、术语解释、历史对比"""
import json
import logging
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.base import get_vision_llm, get_llm, safe_llm_call, safe_tool_call

logger = logging.getLogger(__name__)


# ===== 常见化验指标参考范围 =====
_LAB_REFERENCES = {
    "总胆固醇": {"normal_range": "< 5.2 mmol/L", "borderline": "5.2-6.2", "high": "> 6.2", "unit": "mmol/L"},
    "低密度脂蛋白": {"normal_range": "< 3.4 mmol/L", "borderline": "3.4-4.1", "high": "> 4.1", "unit": "mmol/L"},
    "高密度脂蛋白": {"normal_range": "> 1.0 mmol/L", "note": "偏低", "unit": "mmol/L"},
    "甘油三酯": {"normal_range": "< 1.7 mmol/L", "borderline": "1.7-2.3", "high": "> 2.3", "unit": "mmol/L"},
    "空腹血糖": {"normal_range": "3.9-6.1 mmol/L", "borderline": "6.1-7.0", "high": "> 7.0", "unit": "mmol/L"},
    "糖化血红蛋白": {"normal_range": "4.0-6.0%", "borderline": "5.7-6.4", "high": "> 6.5", "unit": "%"},
    "尿酸": {"normal_range": "男 208-428 μmol/L, 女 155-357", "high": "超出上限", "unit": "μmol/L"},
    "谷丙转氨酶": {"normal_range": "9-50 U/L", "high": "> 50", "unit": "U/L"},
    "谷草转氨酶": {"normal_range": "15-40 U/L", "high": "> 40", "unit": "U/L"},
    "血肌酐": {"normal_range": "男 53-115 μmol/L, 女 44-97", "unit": "μmol/L"},
    "白细胞": {"normal_range": "3.5-9.5 ×10^9/L", "unit": "×10^9/L"},
    "血红蛋白": {"normal_range": "男 130-175 g/L, 女 115-150", "unit": "g/L"},
    "血小板": {"normal_range": "125-350 ×10^9/L", "unit": "×10^9/L"},
    "C反应蛋白": {"normal_range": "< 10 mg/L", "high": "> 10", "unit": "mg/L"},
}


class LabInput(BaseModel):
    test_name: str = Field(description="化验指标名称，如 '总胆固醇'、'空腹血糖'")


class TermInput(BaseModel):
    term: str = Field(description="医学术语，如 '窦性心律'、'脂肪肝'")


class HistoricalInput(BaseModel):
    test_name: str = Field(description="化验指标名称")


class OCRInput(BaseModel):
    image_base64: str = Field(description="Base64 编码的报告图片")


@tool(args_schema=OCRInput)
async def ocr_medical_report(image_base64: str) -> str:
    """
    OCR 识别体检报告/化验单图片，提取所有指标数据。
    使用多模态 LLM 进行识别，返回结构化的指标列表。
    """
    async def _execute() -> str:
        llm = get_vision_llm()

        system_prompt = (
            "你是医学报告识别专家。请仔细识别图片中的体检报告/化验单信息。\n"
            "提取所有检测指标，以 JSON 数组格式返回：\n"
            "[\n"
            '  {"test_name": "指标名称", "value": "检测值", "unit": "单位", "reference_range": "参考范围", "status": "normal/high/low"}\n'
            "]\n"
            "同时返回报告基本信息（如报告日期、医院）。\n"
            "如果图片不清晰或非医学报告，返回 {\"error\": \"无法识别\"}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "请识别这份体检报告"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            ]),
        ]

        try:
            response = await safe_llm_call(llm, messages)
            return response.content
        except Exception as e:
            logger.error(f"报告 OCR 失败: {e}")
            return json.dumps({"error": f"报告识别失败: {e}"}, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=30, tool_name="ocr_medical_report")


@tool(args_schema=LabInput)
async def lookup_lab_reference(test_name: str) -> str:
    """
    查找化验指标的医学参考范围。
    返回正常范围、临界值、异常值标准。
    """
    async def _execute() -> str:
        test_clean = test_name.strip()
        ref = _LAB_REFERENCES.get(test_clean)

        if not ref:
            # 模糊匹配
            for name, data in _LAB_REFERENCES.items():
                if test_clean in name or name in test_clean:
                    ref = data
                    test_clean = name
                    break

        if not ref:
            return json.dumps({
                "error": f"未找到 '{test_name}' 的参考范围",
                "suggestion": "请确认指标名称",
            }, ensure_ascii=False)

        return json.dumps({
            "test_name": test_clean,
            **ref,
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=5, tool_name="lookup_lab_reference")


@tool(args_schema=HistoricalInput)
async def get_historical_lab_values(test_name: str) -> str:
    """
    获取用户某项化验指标的历史记录（从长期记忆中检索）。
    用于趋势分析（如：半年前血糖 5.1 → 现在 6.3）。
    """
    async def _execute() -> str:
        from app.memory.manager import memory_manager
        query = f"{test_name} 化验 检测 指标"
        recalls = await memory_manager.recall("current_user", query, top_k=5)

        history = []
        for r in recalls:
            if r.get("event_type") in ("health_event", "diagnosis"):
                history.append({
                    "summary": r.get("summary", ""),
                    "timestamp": r.get("timestamp", ""),
                    "details": r.get("details", {}),
                })

        if not history:
            return json.dumps({
                "test_name": test_name,
                "history": [],
                "note": "未找到该指标的历史记录",
            }, ensure_ascii=False)

        return json.dumps({
            "test_name": test_name,
            "history": history,
            "count": len(history),
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=10, tool_name="get_historical_lab_values")


@tool(args_schema=TermInput)
async def explain_medical_term(term: str) -> str:
    """
    用通俗语言解释医学术语，帮助用户理解报告内容。
    """
    async def _execute() -> str:
        llm = get_llm()

        system_prompt = (
            "你是医学科普专家。请用通俗易懂的语言解释医学术语，"
            "让没有医学背景的普通人也能理解。\n"
            "解释包括：\n"
            "1. 这个术语是什么意思\n"
            "2. 正常情况应该是怎样的\n"
            "3. 异常意味着什么\n"
            "4. 需要注意什么\n"
            "回答控制在 200 字以内。"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请解释：{term}"),
        ]

        try:
            response = await safe_llm_call(llm, messages)
            return response.content
        except Exception as e:
            return f"术语解释失败: {e}"

    return await safe_tool_call(_execute, timeout=15, tool_name="explain_medical_term")


@tool
async def get_health_events(tags: list[str] = None) -> str:
    """
    搜索用户的历史健康事件（症状记录、就医记录、诊断结果等）。
    可按标签过滤。
    """
    async def _execute() -> str:
        from app.memory.manager import memory_manager
        query = " ".join(tags) if tags else "健康事件 症状 就诊"
        recalls = await memory_manager.recall("current_user", query, top_k=10)

        events = []
        for r in recalls:
            if r.get("event_type") in ("health_event", "diagnosis", "medication_change"):
                events.append({
                    "summary": r.get("summary", ""),
                    "event_type": r.get("event_type", ""),
                    "timestamp": r.get("timestamp", ""),
                    "details": r.get("details", {}),
                })

        return json.dumps({
            "events": events,
            "count": len(events),
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=10, tool_name="get_health_events")
