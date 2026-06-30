"""ChromaDB 可视检查脚本 - 查看向量数据库内容"""
import sys
sys.path.insert(0, '.')

from app.memory.vector_store import init_vector_store, is_available
from app.config import settings

# 1. 初始化
init_vector_store()
print(f"向量库路径: {settings.CHROMA_PERSIST_DIR}")
print(f"向量库可用: {is_available()}")
print()

if not is_available():
    print("❌ 向量库不可用，请先配置 EMBEDDING_API_KEY")
    sys.exit(1)

# 2. 获取底层 collection 对象
from app.memory.vector_store import _health_events_collection

col = _health_events_collection
print(f"集合名称: {col.name}")
print(f"集合总文档数: {col.count()}")
print()

# 3. 获取所有数据
if col.count() > 0:
    results = col.get(
        limit=50,
        include=["documents", "metadatas", "embeddings"]
    )
    
    print(f"{'ID':<38} | {'类型':<20} | {'时间':<22} | 内容摘要")
    print("-" * 120)
    
    for i, doc_id in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        doc = results["documents"][i]
        emb = results["embeddings"][i] if results.get("embeddings") else []
        
        user_id = meta.get("user_id", "?")
        event_type = meta.get("event_type", "?")
        timestamp = meta.get("timestamp", "?")
        agent = meta.get("source_agent", "?")
        
        print(f"{doc_id:<38} | {event_type:<20} | {timestamp[:19]:<22} | {doc[:60]}")
        print(f"  └─ 用户: {user_id} | 来源: {agent} | 向量维度: {len(emb)}")
        print()
else:
    print("⚠️ 集合为空，还没有存入任何健康事件")
    print()
    print("启动应用并完成一次对话后，事件会被自动存入")

# 4. 测试语义搜索
print("=" * 60)
print("测试语义搜索")
print("=" * 60)

test_queries = ["头晕", "用药", "体检", "血压"]
import asyncio
from app.memory.vector_store import search_health_events

async def test_search():
    for q in test_queries:
        results = await search_health_events("default_user", q, top_k=3)
        print(f"\n搜索: '{q}'")
        if not results:
            print("  (无结果)")
        for r in results:
            sim = r.get("similarity", 0)
            bar = "█" * int(sim * 20)
            print(f"  [{bar}] {sim:.3f} | {r['summary'][:60]}")

asyncio.run(test_search())
