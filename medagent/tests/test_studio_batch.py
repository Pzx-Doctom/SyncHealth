"""
通过 LangGraph Studio API 批量执行测试案例。
用法：
  1. 先启动 Studio:  langgraph dev
  2. 再运行本脚本:    python tests/test_studio_batch.py

每条测试案例会在 Studio UI 中生成一条独立的 Trace，可可视化查看。
"""
import asyncio
import sys

from langgraph_sdk import get_client

# test_quick.py 中的 6 个测试案例
TEST_CASES = [
    {
        "title": "测试案例 1: 睡眠问题咨询",
        "user_query": "我最近晚上总是睡不好，凌晨三四点就醒了，有什么建议吗？",
    },
    {
        "title": "测试案例 2: 紧急胸痛",
        "user_query": "我胸口疼得厉害，喘不上气，怎么办？",
    },
    {
        "title": "测试案例 3: 用药咨询",
        "user_query": "我最近在吃布洛芬和阿司匹林，这两种药能不能一起吃？",
    },
    {
        "title": "测试案例 4: 模糊输入",
        "user_query": "我不舒服",
    },
    {
        "title": "测试案例 5: 查找附近医院（触发高德地图 API）",
        "user_query": "我最近感觉心脏不太舒服，想去做个检查，附近有什么医院推荐吗？",
    },
    {
        "title": "测试案例 6: 买药需求（触发药店查询）",
        "user_query": "我感冒了想买点药，附近哪里有药店？",
    },
]

STUDIO_URL = "http://127.0.0.1:2024"
GRAPH_NAME = "medagent"
DEFAULT_USER_ID = "test_user_001"


async def run_one(client, assistant_id: str, case: dict, index: int) -> dict:
    """执行单个测试案例"""
    title = case["title"]
    query = case["user_query"]

    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"  👤 输入: {query}")
    print(f"{'=' * 60}")

    # 1. 创建一个新 thread（每条 case 独立）
    thread = await client.threads.create()

    # 2. 构造图的输入 state（匹配 AgentState 的字段）
    input_state = {
        "user_id": DEFAULT_USER_ID,
        "user_query": query,
        "messages": [],  # Studio 需要 messages 字段存在
    }

    # 3. 调用图执行（SDK 0.4.x 用 assistant_id 而非 assistant_key）
    try:
        result = await client.runs.wait(
            thread_id=thread["thread_id"],
            assistant_id=assistant_id,
            input=input_state,
        )
    except Exception as e:
        print(f"  ❌ 执行失败: {e}")
        return {"title": title, "status": "error", "error": str(e), "thread_id": thread["thread_id"]}

    # 4. 解析结果
    if result and result.get("final_response"):
        resp = result["final_response"]
        # 截断展示
        preview = resp[:200] + ("..." if len(resp) > 200 else "")
        print(f"  💬 回复: {preview}")

        # 工具调用
        tool_calls = result.get("tool_calls", [])
        print(f"  🔧 工具调用: {len(tool_calls)} 次")
        for tc in tool_calls:
            print(f"     - [{tc.get('agent', '?')}] {tc.get('tool', '?')}")

        # 路由
        route = result.get("agent_route", [])
        if route:
            path = " → ".join(f"{r['from_agent']}→{r['to_agent']}" for r in route)
            print(f"  🗺  路由: {path}")

        print(f"  📋 意图: {result.get('intent', '?')} | 紧急度: {result.get('severity', '?')}")

        if result.get("error"):
            print(f"  ⚠️ 错误: {result['error']}")

        return {
            "title": title,
            "status": "success" if not result.get("error") else "partial",
            "thread_id": thread["thread_id"],
        }
    else:
        print(f"  ⚠️ 未获取到 final_response")
        print(f"  完整结果 keys: {list(result.keys()) if result else 'None'}")
        return {
            "title": title,
            "status": "no_response",
            "thread_id": thread["thread_id"],
        }


async def main():
    print("🚀 LangGraph Studio 批量测试")
    print(f"   Studio API: {STUDIO_URL}")
    print(f"   Graph:      {GRAPH_NAME}")
    print(f"   测试案例数:  {len(TEST_CASES)}")
    print()
    print("⚠️  请确保已运行: langgraph dev")
    print()

    # 连接 Studio
    try:
        client = get_client(url=STUDIO_URL)
        # 查询可用的 assistants（langgraph dev 会自动注册一个默认 assistant）
        assistants = await client.assistants.search()
        if not assistants:
            print(f"❌ Studio 没有可用的 assistant，请检查 langgraph.json 配置")
            sys.exit(1)
        # 取第一个 assistant（langgraph dev 默认会创建一个名为 "agent" 的 assistant）
        assistant = assistants[0]
        assistant_id = assistant["assistant_id"]
        print(f"✅ 已连接 Studio，使用 assistant: {assistant.get('name', 'agent')} (id: {assistant_id[:8]}...)")
    except Exception as e:
        print(f"❌ 无法连接 Studio ({STUDIO_URL}): {e}")
        print("   请先运行: langgraph dev")
        sys.exit(1)

    # 逐个执行
    results = []
    for i, case in enumerate(TEST_CASES, 1):
        result = await run_one(client, assistant_id, case, i)
        results.append(result)

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  📊 测试汇总")
    print(f"{'=' * 60}")
    for r in results:
        icon = {"success": "✅", "partial": "⚠️", "error": "❌", "no_response": "❓"}.get(r["status"], "?")
        print(f"  {icon} {r['title']}  (thread: {r['thread_id'][:8]}...)")

    print(f"\n💡 在 Studio UI 中查看完整 Trace:")
    print(f"   https://smith.langchain.com/studio/?baseUrl={STUDIO_URL}")
    print(f"   每个 thread 对应一条测试案例的可视化执行链路")


if __name__ == "__main__":
    asyncio.run(main())
