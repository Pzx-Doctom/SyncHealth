"""测试高德地图 API 连通性"""
import asyncio
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.tools.location import search_nearby_medical


async def test():
    print(f"AMAP_API_KEY: {settings.AMAP_API_KEY[:10]}..." if settings.AMAP_API_KEY else "AMAP_API_KEY: 未配置!")
    print()

    # 直接传入位置测试
    print("=== 测试 1: 直接传入位置（深圳南山科技园）===")
    result = await search_nearby_medical.ainvoke({
        "query": "医院",
        "location": "22.5431,113.9445",  # 深圳南山科技园 lat,lng
        "place_type": "hospital",
        "radius": 5000,
        "max_results": 5,
    })
    print(f"结果: {result[:500]}")
    print()

    # 测试药店
    print("=== 测试 2: 药店查询 ===")
    result = await search_nearby_medical.ainvoke({
        "query": "药店",
        "location": "22.5431,113.9445",
        "place_type": "pharmacy",
        "radius": 3000,
        "max_results": 3,
    })
    print(f"结果: {result[:500]}")


if __name__ == "__main__":
    asyncio.run(test())
