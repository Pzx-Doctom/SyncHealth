"""MCP Server 端点 - 暴露 SyncHealth 健康数据查询工具供 MedAgent Hub 调用"""
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import ActivitySample
from app.models.heart import HeartRate, HRVSample
from app.models.sleep import SleepSession
from app.models.vitals import BloodOxygenSample, BodyTemperatureSample, RespiratoryRateSample
from app.models.workout import WorkoutRecord
from app.services.dashboard_service import get_health_score as calculate_health_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


def _resolve_user_id(raw: object) -> int:
    """
    将 MedAgent Hub 传来的 user_id 解析为 backend 使用的整数 ID。
    - 整数 → 直接返回
    - 数字字符串 → 转 int
    - 非数字字符串（如 "test_user_001"）→ 提取末尾数字，否则默认 1
    """
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        if raw.isdigit():
            return int(raw)
        import re
        m = re.search(r"\d+", raw)
        if m:
            return int(m.group())
    return 1


# ===== 工具定义 =====
MCP_TOOLS = [
    {
        "name": "get_heart_rate_trend",
        "description": "获取用户最近 N 天的心率趋势数据，包括平均值、静息心率、异常波动",
        "parameters": {"days": {"type": "integer", "default": 7}},
    },
    {
        "name": "get_sleep_analysis",
        "description": "获取用户最近 N 天的睡眠深度分析",
        "parameters": {"days": {"type": "integer", "default": 7}},
    },
    {
        "name": "get_activity_summary",
        "description": "获取用户最近 N 天的活动数据摘要（步数、卡路里、距离）",
        "parameters": {"days": {"type": "integer", "default": 7}},
    },
    {
        "name": "get_health_score",
        "description": "获取用户的综合健康评分（0-100）",
        "parameters": {},
    },
    {
        "name": "get_workout_history",
        "description": "获取用户最近 N 天的运动记录历史",
        "parameters": {"days": {"type": "integer", "default": 7}},
    },
    {
        "name": "get_vital_signs",
        "description": "获取用户最近 N 天的生命体征（血氧、体温、呼吸频率）",
        "parameters": {"days": {"type": "integer", "default": 7}},
    },
    {
        "name": "search_medical_knowledge",
        "description": "搜索 Dify 医学知识库获取相关参考信息",
        "parameters": {"query": {"type": "string"}},
    },
    {
        "name": "search_fitness_knowledge",
        "description": "搜索运动健康知识库",
        "parameters": {"query": {"type": "string"}},
    },
]


@router.get("/health")
async def mcp_health():
    """MCP 服务健康检查"""
    return {"status": "ok", "service": "SyncHealth MCP Server"}


@router.get("/tools")
async def list_tools():
    """列出 MCP 暴露的所有工具"""
    return {"tools": MCP_TOOLS}


@router.post("/health-context")
async def get_health_context(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """获取用户健康数据上下文（综合查询）"""
    user_id = _resolve_user_id(body.get("user_id", 1))
    query = body.get("query", "")

    try:
        from app.services.ai.context_builder import build_health_context
        context = await build_health_context(db, user_id, query)
        return {"context": context}
    except Exception as e:
        logger.error(f"MCP health-context 查询失败 (user_id={user_id}): {e}")
        return {"context": "", "error": str(e)}


@router.post("/tools/call")
async def call_tool(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """调用指定的 MCP 工具"""
    tool_name = body.get("tool_name")
    args = body.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="缺少 tool_name")

    # 默认 user_id=1（实际应从认证获取）
    user_id = _resolve_user_id(args.pop("user_id", 1))

    try:
        if tool_name == "get_heart_rate_trend":
            result = await _get_heart_rate_trend(db, user_id, args.get("days", 7))
        elif tool_name == "get_sleep_analysis":
            result = await _get_sleep_analysis(db, user_id, args.get("days", 7))
        elif tool_name == "get_activity_summary":
            result = await _get_activity_summary(db, user_id, args.get("days", 7))
        elif tool_name == "get_health_score":
            result = await _get_health_score(db, user_id)
        elif tool_name == "get_workout_history":
            result = await _get_workout_history(db, user_id, args.get("days", 7))
        elif tool_name == "get_vital_signs":
            result = await _get_vital_signs(db, user_id, args.get("days", 7))
        elif tool_name == "search_medical_knowledge":
            result = await _search_knowledge(args.get("query", ""))
        elif tool_name == "search_fitness_knowledge":
            result = await _search_knowledge(args.get("query", ""))
        else:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")

        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP 工具调用失败 {tool_name}: {e}")
        return {"result": json.dumps({"error": str(e)}, ensure_ascii=False)}


# ===== 工具实现 =====

async def _get_heart_rate_trend(db: AsyncSession, user_id: int, days: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.avg(HeartRate.bpm),
            func.min(HeartRate.bpm),
            func.max(HeartRate.bpm),
        ).where(
            HeartRate.user_id == user_id,
            HeartRate.measurement_type == "heart_rate",
            HeartRate.recorded_at >= since,
        )
    )
    row = result.one_or_none()

    if not row or not row[0]:
        return json.dumps({"error": "无心率数据"}, ensure_ascii=False)

    return json.dumps({
        "period_days": days,
        "avg_bpm": round(row[0], 1),
        "min_bpm": int(row[1]),
        "max_bpm": int(row[2]),
        "note": f"近 {days} 天平均心率 {row[0]:.0f} bpm",
    }, ensure_ascii=False)


async def _get_sleep_analysis(db: AsyncSession, user_id: int, days: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    result = await db.execute(
        select(SleepSession).where(
            SleepSession.user_id == user_id,
            SleepSession.recorded_at >= since,
        ).order_by(SleepSession.recorded_at.desc()).limit(days)
    )
    sessions = result.scalars().all()

    if not sessions:
        return json.dumps({"error": "无睡眠数据"}, ensure_ascii=False)

    avg_hours = sum(s.total_duration_minutes for s in sessions) / len(sessions) / 60
    return json.dumps({
        "period_days": days,
        "avg_sleep_hours": round(avg_hours, 1),
        "sessions_count": len(sessions),
        "note": f"近 {days} 天平均睡眠 {avg_hours:.1f} 小时",
    }, ensure_ascii=False)


async def _get_activity_summary(db: AsyncSession, user_id: int, days: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    result = await db.execute(
        select(
            ActivitySample.metric_type,
            func.sum(ActivitySample.value),
        ).where(
            ActivitySample.user_id == user_id,
            ActivitySample.recorded_at >= since,
        ).group_by(ActivitySample.metric_type)
    )
    rows = result.all()

    if not rows:
        return json.dumps({"error": "无活动数据"}, ensure_ascii=False)

    data = {row[0]: round(row[1], 1) for row in rows}
    return json.dumps({
        "period_days": days,
        "total_steps": data.get("steps", 0),
        "daily_avg_steps": round(data.get("steps", 0) / days),
        "total_energy_kcal": data.get("active_energy", data.get("energy", 0)),
        "total_distance_km": round(data.get("distance", 0) / 1000, 1) if data.get("distance") else 0,
    }, ensure_ascii=False)


async def _get_health_score(db: AsyncSession, user_id: int) -> str:
    try:
        score_data = await calculate_health_score(db, user_id)
        # get_health_score 返回 HealthScore 对象，提取 overall_score
        overall = getattr(score_data, "overall_score", None)
        if overall is None and isinstance(score_data, dict):
            overall = score_data.get("overall_score")
        return json.dumps({
            "health_score": overall if overall is not None else score_data,
            "user_id": user_id,
            "activity_score": getattr(score_data, "activity_score", None),
            "sleep_score": getattr(score_data, "sleep_score", None),
            "heart_score": getattr(score_data, "heart_score", None),
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"健康评分计算失败: {e}"}, ensure_ascii=False)


async def _get_workout_history(db: AsyncSession, user_id: int, days: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    result = await db.execute(
        select(WorkoutRecord).where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.recorded_at >= since,
        ).order_by(WorkoutRecord.recorded_at.desc()).limit(10)
    )
    workouts = result.scalars().all()

    if not workouts:
        return json.dumps({"error": "无运动记录"}, ensure_ascii=False)

    return json.dumps({
        "count": len(workouts),
        "workouts": [
            {
                "type": w.workout_type,
                "duration_min": round(w.duration_seconds / 60),
                "energy_kcal": w.active_energy_kcal or 0,
                "date": w.start_time.strftime("%Y-%m-%d") if w.start_time else "",
            }
            for w in workouts
        ],
    }, ensure_ascii=False)


async def _get_vital_signs(db: AsyncSession, user_id: int, days: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # 血氧
    spo2_result = await db.execute(
        select(func.avg(BloodOxygenSample.spo2_percent)).where(
            BloodOxygenSample.user_id == user_id,
            BloodOxygenSample.recorded_at >= since,
        )
    )
    avg_spo2 = spo2_result.scalar()

    # 体温
    temp_result = await db.execute(
        select(func.avg(BodyTemperatureSample.temperature)).where(
            BodyTemperatureSample.user_id == user_id,
            BodyTemperatureSample.recorded_at >= since,
        )
    )
    avg_temp = temp_result.scalar()

    # 呼吸频率
    resp_result = await db.execute(
        select(func.avg(RespiratoryRateSample.rate)).where(
            RespiratoryRateSample.user_id == user_id,
            RespiratoryRateSample.recorded_at >= since,
        )
    )
    avg_resp = resp_result.scalar()

    return json.dumps({
        "period_days": days,
        "avg_spo2": round(avg_spo2, 1) if avg_spo2 else None,
        "avg_temperature": round(avg_temp, 1) if avg_temp else None,
        "avg_respiratory_rate": round(avg_resp, 1) if avg_resp else None,
    }, ensure_ascii=False)


async def _search_knowledge(query: str) -> str:
    """搜索 Dify 知识库"""
    if not query:
        return json.dumps({"error": "查询不能为空"}, ensure_ascii=False)

    try:
        from app.services.ai.dify_retriever import retrieve_from_dify, format_dify_context
        records = await retrieve_from_dify(query)
        context = format_dify_context(records)
        return context or json.dumps({"result": "未找到相关知识"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"知识检索失败: {e}"}, ensure_ascii=False)
