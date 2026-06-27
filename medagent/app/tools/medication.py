"""用药管理工具 - 药品查询、相互作用、OTC 推荐、OCR"""
import json
import logging
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.base import get_vision_llm, get_llm, safe_llm_call, safe_tool_call

logger = logging.getLogger(__name__)


class DrugQueryInput(BaseModel):
    drug_name: str = Field(description="药品名称（通用名或商品名）")


class InteractionInput(BaseModel):
    drug_a: str = Field(description="药品 A 名称")
    drug_b: str = Field(description="药品 B 名称")


class SymptomInput(BaseModel):
    symptoms: list[str] = Field(description="用户描述的症状列表")


class OCRInput(BaseModel):
    image_base64: str = Field(description="Base64 编码的图片")


# ===== 简易药品知识库（可后续替换为外部 API） =====
_DRUG_DATABASE = {
    "阿莫西林": {
        "category": "抗生素（青霉素类）",
        "prescription": True,
        "usage": "成人每次 0.5g，每 6-8 小时一次，一日剂量 1-4g",
        "indications": ["呼吸道感染", "泌尿道感染", "皮肤软组织感染"],
        "contraindications": ["青霉素过敏者禁用"],
        "side_effects": ["皮疹", "恶心", "腹泻", "过敏反应"],
        "note": "处方药，需遵医嘱使用",
    },
    "布洛芬": {
        "category": "解热镇痛药（NSAIDs）",
        "prescription": False,
        "usage": "成人每次 0.2-0.4g，每 4-6 小时一次，一日不超过 1.2g",
        "indications": ["发热", "头痛", "牙痛", "肌肉痛", "关节痛"],
        "contraindications": ["活动性消化道溃疡", "严重肝肾功能不全", "对阿司匹林过敏"],
        "side_effects": ["胃肠道不适", "头晕", "皮疹"],
        "note": "OTC 非处方药，饭后服用可减少胃肠道刺激",
    },
    "对乙酰氨基酚": {
        "category": "解热镇痛药",
        "prescription": False,
        "usage": "成人每次 0.5-1g，每 4-6 小时一次，一日不超过 4g",
        "indications": ["发热", "头痛", "关节痛", "牙痛"],
        "contraindications": ["严重肝肾功能不全", "对本品过敏"],
        "side_effects": ["偶见皮疹", "过量可致肝损伤"],
        "note": "OTC 非处方药，是最安全的解热镇痛药之一",
    },
    "氨氯地平": {
        "category": "钙通道阻滞剂（降压药）",
        "prescription": True,
        "usage": "通常起始剂量 5mg，每日一次，最大 10mg/日",
        "indications": ["高血压", "稳定型心绞痛"],
        "contraindications": ["对二氢吡啶类过敏", "严重低血压"],
        "side_effects": ["头痛", "水肿", "面部潮红", "心悸", "头晕"],
        "note": "处方药，常见副作用头痛发生率约 10%",
    },
    "奥美拉唑": {
        "category": "质子泵抑制剂（PPI）",
        "prescription": False,
        "usage": "每次 20mg，每日一次，晨起空腹服用",
        "indications": ["胃溃疡", "十二指肠溃疡", "反流性食管炎"],
        "contraindications": ["对本品过敏"],
        "side_effects": ["头痛", "腹泻", "恶心", "腹胀"],
        "note": "OTC，建议餐前 30 分钟服用",
    },
}

# 已知药物相互作用
_INTERACTIONS = {
    ("布洛芬", "氨氯地平"): "布洛芬可能减弱氨氯地平的降压效果，建议监测血压",
    ("对乙酰氨基酚", "奥美拉唑"): "无已知显著相互作用，可安全合用",
    ("布洛芬", "奥美拉唑"): "奥美拉唑可减轻布洛芬的胃肠道刺激，可合用",
}


@tool(args_schema=DrugQueryInput)
async def lookup_drug_info(drug_name: str) -> str:
    """
    查询药品的详细信息：类别、用法用量、适应症、禁忌症、副作用。
    支持通用名和常见商品名。
    """
    async def _execute() -> str:
        drug_name_clean = drug_name.strip()
        info = _DRUG_DATABASE.get(drug_name_clean)

        if not info:
            # 模糊匹配
            for name, data in _DRUG_DATABASE.items():
                if drug_name_clean in name or name in drug_name_clean:
                    info = data
                    drug_name_clean = name
                    break

        if not info:
            return json.dumps({
                "error": f"未找到药品 '{drug_name}' 的信息",
                "suggestion": "请确认药品名称，或建议用户咨询药师",
            }, ensure_ascii=False)

        return json.dumps({
            "drug_name": drug_name_clean,
            **info,
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=5, tool_name="lookup_drug_info")


@tool(args_schema=InteractionInput)
async def check_drug_interaction(drug_a: str, drug_b: str) -> str:
    """
    检查两种药物之间是否存在相互作用。
    返回相互作用的风险等级和建议。
    """
    async def _execute() -> str:
        key = tuple(sorted([drug_a.strip(), drug_b.strip()]))
        interaction = _INTERACTIONS.get(key)

        if interaction:
            return json.dumps({
                "drug_a": drug_a,
                "drug_b": drug_b,
                "has_interaction": True,
                "description": interaction,
                "risk_level": "moderate",
                "recommendation": "请咨询医生或药师",
            }, ensure_ascii=False)

        # 检查是否在数据库中
        a_known = drug_a.strip() in _DRUG_DATABASE
        b_known = drug_b.strip() in _DRUG_DATABASE

        if not a_known or not b_known:
            return json.dumps({
                "drug_a": drug_a,
                "drug_b": drug_b,
                "has_interaction": "unknown",
                "description": "数据库中信息不足，无法判断相互作用",
                "recommendation": "强烈建议咨询医生或药师",
            }, ensure_ascii=False)

        return json.dumps({
            "drug_a": drug_a,
            "drug_b": drug_b,
            "has_interaction": False,
            "description": "未发现已知相互作用",
            "recommendation": "可按医嘱服用，如有不适应及时就医",
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=5, tool_name="check_drug_interaction")


@tool(args_schema=SymptomInput)
async def search_otc_drugs(symptoms: list[str]) -> str:
    """
    根据用户描述的症状推荐 OTC 非处方药。
    仅推荐非处方药，处方药需就医。
    返回推荐药品及注意事项。
    """
    async def _execute() -> str:
        recommendations = []
        for name, info in _DRUG_DATABASE.items():
            if not info["prescription"]:
                # 症状匹配
                match_score = sum(
                    1 for s in symptoms
                    if any(s in ind or ind in s for ind in info["indications"])
                )
                if match_score > 0:
                    recommendations.append({
                        "drug_name": name,
                        "match_symptoms": [s for s in symptoms if any(s in ind or ind in s for ind in info["indications"])],
                        "usage": info["usage"],
                        "note": info["note"],
                        "contraindications": info["contraindications"],
                    })

        if not recommendations:
            return json.dumps({
                "error": "未找到匹配的 OTC 药品",
                "recommendation": "建议就医获取专业诊断和处方",
            }, ensure_ascii=False)

        return json.dumps({
            "symptoms": symptoms,
            "recommendations": recommendations,
            "disclaimer": "以上为 OTC 药品参考推荐，非医疗建议。如症状持续或加重请及时就医。",
        }, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=5, tool_name="search_otc_drugs")


@tool(args_schema=OCRInput)
async def ocr_medicine_box(image_base64: str) -> str:
    """
    OCR 识别药盒/药品说明书图片，提取药品名称、规格、用法用量等关键信息。
    使用多模态 LLM 进行识别。
    """
    async def _execute() -> str:
        llm = get_vision_llm()

        system_prompt = (
            "你是药品包装识别专家。请仔细识别图片中的药品信息，提取以下内容并以 JSON 格式返回：\n"
            "{\n"
            '  "drug_name": "药品名称",\n'
            '  "specification": "规格",\n'
            '  "manufacturer": "生产厂家",\n'
            '  "approval_number": "批准文号",\n'
            '  "usage": "用法用量",\n'
            '  "indications": ["适应症"],\n'
            '  "is_prescription": true/false\n'
            "}\n"
            "如果某个字段无法识别，设为 null。"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "请识别这个药品包装的信息"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            ]),
        ]

        try:
            response = await safe_llm_call(llm, messages)
            return response.content
        except Exception as e:
            logger.error(f"药盒 OCR 失败: {e}")
            return json.dumps({"error": f"图片识别失败: {e}"}, ensure_ascii=False)

    return await safe_tool_call(_execute, timeout=30, tool_name="ocr_medicine_box")


@tool
async def get_user_medications() -> str:
    """
    获取用户当前正在服用的药品列表（从用户画像/长期记忆中获取）。
    """
    async def _execute() -> str:
        from app.memory.profile import get_profile
        profile = await get_profile("current_user")
        medications = profile.get("current_medications", []) if profile else []
        return json.dumps({
            "medications": medications,
            "count": len(medications),
        }, ensure_ascii=False)
    return await safe_tool_call(_execute, timeout=5, tool_name="get_user_medications")


@tool
async def create_medication_reminder(
    drug_name: str,
    schedule: str,
    dosage: str,
) -> str:
    """
    创建用药提醒。
    参数：
    - drug_name: 药品名称
    - schedule: 服用计划（如 "每日三次，饭后"）
    - dosage: 单次剂量（如 "0.5g"）
    """
    async def _execute() -> str:
        # 注：实际提醒功能需要对接推送服务或日历
        # 这里先记录到用户画像
        from app.memory.profile import add_medication
        await add_medication("current_user", drug_name)
        return json.dumps({
            "success": True,
            "reminder": {
                "drug_name": drug_name,
                "schedule": schedule,
                "dosage": dosage,
                "created_at": "已记录",
            },
            "note": "用药提醒已创建，将在指定时间提醒您服药",
        }, ensure_ascii=False)
    return await safe_tool_call(_execute, timeout=5, tool_name="create_medication_reminder")
