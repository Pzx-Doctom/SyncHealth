"""健康数据工具 - 通过 MCP 客户端从 SyncHealth 获取"""
import json
import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agents.base import safe_tool_call

logger = logging.getLogger(__name__)


class DaysInput(BaseModel):
    days: int = Field(default=7, description="查询最近 N 天的数据，默认 7")


class QueryInput(BaseModel):
    query: str = Field(description="搜索关键词")


@tool
async def get_heart_rate_trend(days: int = 7) -> str:
    """
    获取用户最近 N 天的心率趋势数据，包括平均值、静息心率、异常波动。
    数据来源：SyncHealth 可穿戴设备（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "get_heart_rate_trend", {"days": days}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="get_heart_rate_trend")


@tool
async def get_sleep_analysis(days: int = 7) -> str:
    """
    获取用户最近 N 天的睡眠深度分析，包括总时长、深度睡眠占比、REM 占比、睡眠效率。
    数据来源：SyncHealth 可穿戴设备（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "get_sleep_analysis", {"days": days}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="get_sleep_analysis")


@tool
async def get_activity_summary(days: int = 7) -> str:
    """
    获取用户最近 N 天的活动数据摘要，包括步数、卡路里、距离、爬楼层数、站立时间。
    数据来源：SyncHealth 可穿戴设备（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "get_activity_summary", {"days": days}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="get_activity_summary")


@tool
async def get_health_score() -> str:
    """
    获取用户的综合健康评分（0-100），基于心率、睡眠、活动等多维度计算。
    数据来源：SyncHealth Dashboard（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool("get_health_score", {})
    return await safe_tool_call(_execute, timeout=30, tool_name="get_health_score")


@tool
async def get_workout_history(days: int = 7) -> str:
    """
    获取用户最近 N 天的运动记录历史，包括运动类型、时长、心率区间。
    数据来源：SyncHealth 可穿戴设备（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "get_workout_history", {"days": days}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="get_workout_history")


@tool
async def get_vital_signs(days: int = 7) -> str:
    """
    获取用户最近 N 天的生命体征数据（血氧、体温、呼吸频率）。
    数据来源：SyncHealth 可穿戴设备（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "get_vital_signs", {"days": days}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="get_vital_signs")
