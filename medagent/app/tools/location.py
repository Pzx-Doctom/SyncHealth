"""附近医疗机构查询工具 - 共享 Tool（被所有专家 Agent 调用）"""
import json
import logging
from typing import Optional

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config import settings
from app.agents.base import safe_tool_call

logger = logging.getLogger(__name__)


class NearbyMedicalInput(BaseModel):
    """附近医疗机构查询参数"""
    query: str = Field(
        description="搜索关键词，如 '医院'、'药店'、'急诊'、'三甲医院'、'24小时药店'"
    )
    location: Optional[str] = Field(
        default=None,
        description="用户位置 'lat,lng'（纬度,经度）。如不提供则尝试从用户画像获取"
    )
    place_type: str = Field(
        default="all",
        description="机构类型：hospital=医院, pharmacy=药店, clinic=诊所, all=全部"
    )
    radius: int = Field(default=5000, description="搜索半径（米），默认5000")
    max_results: int = Field(default=10, description="最大返回结果数")


# 高德地图 POI 类型码
_AMAP_TYPE_MAP = {
    "hospital": "090000",      # 医疗保健-综合医院
    "pharmacy": "090200",      # 医疗保健-药房药店
    "clinic": "090100",        # 医疗保健-专科医院/诊所
    "all": "090000|090100|090200",
}

_TYPE_LABELS = {
    "hospital": "医院",
    "pharmacy": "药店",
    "clinic": "诊所",
    "all": "医疗机构",
}


@tool(args_schema=NearbyMedicalInput)
async def search_nearby_medical(
    query: str,
    location: Optional[str] = None,
    place_type: str = "all",
    radius: int = 5000,
    max_results: int = 10,
) -> str:
    """
    搜索附近的医院、药店、诊所等医疗机构。

    适用场景：
    - 用户需要找附近的医院就医
    - 用户需要找药店买药
    - 紧急情况下查找最近的急诊
    - 用户想了解周边医疗资源

    返回：距离、地址、电话、评分、是否有急诊、是否24小时等信息。
    """
    async def _execute() -> str:
        # 获取位置（如未提供则从用户画像查询）
        if not location:
            resolved = await _get_user_location()
            if not resolved:
                return json.dumps({
                    "error": "未获取到用户位置信息",
                    "suggestion": "请提供您的位置信息（例如：深圳市南山区），或授权位置服务",
                }, ensure_ascii=False)
            loc = resolved
        else:
            loc = location

        results = await _call_amap_api(query, loc, place_type, radius, max_results)
        return _format_results(results, place_type)

    return await safe_tool_call(_execute, timeout=30, tool_name="search_nearby_medical")


async def _get_user_location() -> Optional[str]:
    """从用户画像获取位置（需要上下文中的 user_id）"""
    try:
        from app.memory.profile import get_profile
        # 注：实际 user_id 从 context 传递，这里用简化的实现
        # 在 Agent 节点中会注入 user_id 到 tool 的运行上下文
        profile = await get_profile("current_user")
        if profile and profile.get("home_address"):
            geo = await _geocode(profile["home_address"])
            if geo:
                return f"{geo['lat']},{geo['lng']}"
        if profile and profile.get("city"):
            geo = await _geocode(profile["city"])
            if geo:
                return f"{geo['lat']},{geo['lng']}"
    except Exception as e:
        logger.warning(f"获取用户位置失败: {e}")
    return None


async def _geocode(address: str) -> Optional[dict]:
    """地址 → 经纬度转换（高德地理编码 API）"""
    if not settings.AMAP_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params={"key": settings.AMAP_API_KEY, "address": address, "output": "json"},
            )
            data = resp.json()
            if data.get("status") == "1" and data.get("geocodes"):
                # 高德返回 "lng,lat"，转换为 "lat,lng"
                lng, lat = data["geocodes"][0]["location"].split(",")
                return {"lat": lat, "lng": lng}
    except Exception as e:
        logger.warning(f"地理编码失败: {e}")
    return None


async def _call_amap_api(
    keyword: str,
    location: str,
    place_type: str,
    radius: int,
    max_results: int,
) -> list[dict]:
    """调用高德地图周边搜索 API"""
    if not settings.AMAP_API_KEY:
        logger.warning("AMAP_API_KEY 未配置，无法调用地图 API")
        return []

    types = _AMAP_TYPE_MAP.get(place_type, _AMAP_TYPE_MAP["all"])

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/place/around",
                params={
                    "key": settings.AMAP_API_KEY,
                    "location": location,
                    "keywords": keyword,
                    "types": types,
                    "radius": radius,
                    "offset": max_results,
                    "extensions": "all",
                    "output": "json",
                },
            )
            data = resp.json()
            if data.get("status") == "1":
                return data.get("pois", [])
            logger.warning(f"高德 API 返回错误: {data.get('info')}")
            return []
    except Exception as e:
        logger.warning(f"高德 API 调用失败: {e}")
        return []


def _format_results(results: list[dict], place_type: str) -> str:
    """格式化搜索结果"""
    label = _TYPE_LABELS.get(place_type, "医疗机构")

    if not results:
        return f"未找到附近的{label}，建议扩大搜索范围或更换关键词。"

    formatted = []
    for r in results[:10]:
        # 解析是否有急诊/24小时信息（从 tag 字段推断）
        tags = r.get("tag", "").split(";") if r.get("tag") else []
        has_emergency = any("急诊" in t for t in tags)
        is_24h = any("24" in t for t in tags)

        item = {
            "name": r.get("name", "未知"),
            "address": r.get("address", "暂无"),
            "distance": f"{r.get('distance', '?')}米",
            "phone": r.get("tel", "暂无"),
            "type": r.get("type", ""),
            "has_emergency": has_emergency,
            "is_24h": is_24h,
            "tags": tags,
        }
        formatted.append(item)

    return json.dumps({
        "count": len(formatted),
        "query_type": place_type,
        "results": formatted,
        "note": "以上信息仅供参考，建议就医前电话确认",
    }, ensure_ascii=False)
