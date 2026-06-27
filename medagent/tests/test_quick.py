"""快速测试 - 直接 invoke LangGraph，不依赖 WebSocket"""
import asyncio
import json
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.core.state import make_initial_state
from app.core.graph import get_compiled_graph


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_data_sources(final: dict):
    """展示从 MCP / 记忆拉取的数据"""
    health_ctx = final.get("health_context", "")
    memory_ctx = final.get("memory_context", "")

    print("\n📦 数据源:")
    if health_ctx and "不可用" not in health_ctx and health_ctx.strip():
        # 截断展示
        preview = health_ctx[:500] + ("..." if len(health_ctx) > 500 else "")
        print(f"  🏥 健康数据 (MCP): {len(health_ctx)} 字符")
        print(f"     {preview}")
    else:
        print(f"  🏥 健康数据 (MCP): 无 / 降级")

    if memory_ctx and "不可用" not in memory_ctx and "无相关" not in memory_ctx:
        preview = memory_ctx[:300] + ("..." if len(memory_ctx) > 300 else "")
        print(f"  🧠 长期记忆: {len(memory_ctx)} 字符")
        print(f"     {preview}")
    else:
        print(f"  🧠 长期记忆: 无")


def print_tool_calls(final: dict):
    """展示工具调用详情"""
    tool_calls = final.get("tool_calls", [])
    print(f"\n🔧 工具调用: {len(tool_calls)} 次")
    for i, tc in enumerate(tool_calls, 1):
        tool_name = tc.get("tool", "unknown")
        agent = tc.get("agent", "?")
        result_str = tc.get("result", "")
        status = tc.get("status", "?")

        # 尝试解析 result JSON 提取关键信息
        result_preview = result_str[:200]
        try:
            result_data = json.loads(result_str)
            # 提取关键字段做简洁展示
            if "avg_bpm" in result_data:
                result_preview = f"平均心率 {result_data['avg_bpm']} bpm"
            elif "avg_sleep_hours" in result_data:
                result_preview = f"平均睡眠 {result_data['avg_sleep_hours']} 小时"
            elif "daily_avg_steps" in result_data:
                result_preview = f"日均步数 {result_data['daily_avg_steps']}"
            elif "health_score" in result_data:
                result_preview = f"健康评分 {result_data['health_score']}"
            elif "count" in result_data and "workouts" in result_data:
                result_preview = f"运动记录 {result_data['count']} 条"
            elif "error" in result_data:
                result_preview = f"错误: {result_data['error']}"
            else:
                result_preview = result_str[:200]
        except (json.JSONDecodeError, TypeError):
            pass

        icon = "✅" if status == "success" else "❌"
        print(f"  {i}. {icon} [{agent}] {tool_name}")
        print(f"     → {result_preview}")


async def run_test(title: str, query: str, session_id: int, thread_id: str):
    """运行单个测试案例并展示完整结果"""
    print_section(title)

    state = make_initial_state(
        user_id="test_user_001",
        user_query=query,
        session_id=session_id,
    )

    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # 打印用户实际输入
    print(f"👤 用户输入: {query}")

    final = await graph.ainvoke(state, config=config)

    # 基本结果
    print(f"📋 意图: {final.get('intent')}")
    print(f"⚠️  紧急度: {final.get('severity')}")
    print(f"🎯 路由到: {final.get('target_agent') or '(由路由函数决定)'}")
    print(f"🧠 分诊理由: {final.get('triage_reasoning')}")

    # 流转路径
    print(f"\n🗺  流转路径:")
    for r in final.get("agent_route", []):
        print(f"   {r['from_agent']} → {r['to_agent']}")

    # 数据源（MCP 拉取的健康数据 + 记忆召回）
    print_data_sources(final)

    # 工具调用详情
    print_tool_calls(final)

    # 记忆召回
    recalls = final.get("memory_recalls", [])
    if recalls:
        print(f"\n🧠 记忆召回: {len(recalls)} 条")
        for r in recalls:
            print(f"   - {r.get('summary', '')} (相似度: {r.get('similarity', 0):.2f})")

    # 最终回复
    print(f"\n💬 最终回复:")
    print(final.get("final_response", "(无)"))

    # 状态
    if final.get("error"):
        print(f"\n❌ 错误: {final.get('error')}")
    else:
        print(f"\n✅ 测试通过")

    return final


async def main():
    # 检查配置
    if not settings.AI_API_KEY:
        print("❌ 请先在 .env 中配置 AI_API_KEY！")
        return

    print("🚀 MedAgent Hub 快速测试")
    print(f"   LLM:      {settings.AI_MODEL} @ {settings.AI_BASE_URL}")
    print(f"   嵌入模型: {settings.EMBEDDING_MODEL} @ {settings.EMBEDDING_BASE_URL}")
    print(f"   MCP:      {settings.SYNCHEALTH_BASE_URL}")

    # 初始化数据库
    from app.database import init_db
    await init_db()
    print("✅ 数据库表初始化完成")

    # 初始化向量存储
    from app.memory.vector_store import init_vector_store, is_available
    init_vector_store()
    print(f"✅ 向量存储: {'可用' if is_available() else '不可用 (降级)'}")

    # 初始化 MCP 连接
    from app.mcp.client import mcp_client
    await mcp_client.warmup()
    print(f"✅ MCP 连接: {'可用' if mcp_client.is_available else '不可用 (降级)'}")

    # 写入用户位置画像（让 search_nearby_medical 能获取位置）
    from app.memory.profile import update_profile
    await update_profile("current_user", {
        "city": "深圳市南山区",
        "home_address": "深圳市南山区科技园",
    })
    print("✅ 用户画像已写入位置: 深圳市南山区")
    print()

    # 运行测试案例
    await run_test(
        "测试案例 1: 睡眠问题咨询",
        "我最近晚上总是睡不好，凌晨三四点就醒了，有什么建议吗？",
        session_id=1,
        thread_id="test_session_1",
    )

    await run_test(
        "测试案例 2: 紧急胸痛",
        "我胸口疼得厉害，喘不上气，怎么办？",
        session_id=2,
        thread_id="test_session_2",
    )

    await run_test(
        "测试案例 3: 用药咨询",
        "我最近在吃布洛芬和阿司匹林，这两种药能不能一起吃？",
        session_id=3,
        thread_id="test_session_3",
    )

    await run_test(
        "测试案例 4: 模糊输入",
        "我不舒服",
        session_id=4,
        thread_id="test_session_4",
    )

    await run_test(
        "测试案例 5: 查找附近医院（触发高德地图 API）",
        "我最近感觉心脏不太舒服，想去做个检查，附近有什么医院推荐吗？",
        session_id=5,
        thread_id="test_session_5",
    )

    await run_test(
        "测试案例 6: 买药需求（触发药店查询）",
        "我感冒了想买点药，附近哪里有药店？",
        session_id=6,
        thread_id="test_session_6",
    )

    # 清理资源（否则事件循环不会退出）
    await mcp_client.close()

    from app.core.graph import close_graph
    await close_graph()

    from app.database import engine
    await engine.dispose()

    print("\n" + "=" * 60)
    print("  全部测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
