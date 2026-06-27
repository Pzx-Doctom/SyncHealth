"""context_injection 节点 - 数据准备（并行加载三种上下文）"""
import asyncio
import logging

from app.core.state import AgentState
from app.core.errors import MCPConnectionError

logger = logging.getLogger(__name__)


async def context_injection_node(state: AgentState) -> dict:
    """
    数据注入节点 - 在 Triage 之前运行。
    并行加载三种上下文：
    1. health_context  - 通过 MCP 从 SyncHealth 获取健康数据
    2. memory_context  - 从 ChromaDB 检索长期记忆
    3. knowledge_context - 从 RAG 获取医学知识（复用 Dify）

    任何一种上下文加载失败都会优雅降级（返回空字符串），不影响主流程。
    """
    user_id = state["user_id"]
    query = state["user_query"]

    # 并行加载三种上下文（任一失败不影响其他）
    results = await asyncio.gather(
        _load_health_context(user_id, query),
        _load_memory_context(user_id, query),
        _load_knowledge_context(query),
        return_exceptions=True,
    )

    health_context, memory_context, knowledge_context = "", "", ""

    if isinstance(results[0], str):
        health_context = results[0]
    else:
        logger.warning(f"健康上下文加载失败: {results[0]}")

    if isinstance(results[1], str):
        memory_context = results[1]
    else:
        logger.warning(f"记忆上下文加载失败: {results[1]}")

    if isinstance(results[2], str):
        knowledge_context = results[2]
    else:
        logger.warning(f"知识上下文加载失败: {results[2]}")

    return {
        "health_context": health_context,
        "memory_context": memory_context,
        "knowledge_context": knowledge_context,
        "memory_recalls": [],  # 将在 memory 模块填充
    }


async def _load_health_context(user_id: str, query: str) -> str:
    """通过 MCP 客户端获取 SyncHealth 健康数据"""
    from app.mcp.client import mcp_client

    try:
        return await mcp_client.get_health_context(user_id, query)
    except MCPConnectionError as e:
        logger.warning(f"MCP 健康数据获取失败，降级为空: {e}")
        return "（健康数据暂不可用）"
    except Exception as e:
        logger.warning(f"健康上下文加载异常: {e}")
        return "（健康数据暂不可用）"


async def _load_memory_context(user_id: str, query: str) -> str:
    """从长期记忆系统检索相关历史"""
    from app.memory.manager import memory_manager

    try:
        recalls = await memory_manager.recall(user_id, query, top_k=5)
        if not recalls:
            return "（无相关历史记忆）"

        lines = ["## 用户长期记忆召回"]
        for r in recalls:
            lines.append(f"- [{r.get('event_type', 'event')}] {r.get('summary', '')} (相似度: {r.get('similarity', 0):.2f})")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"记忆检索失败，降级为空: {e}")
        return "（长期记忆暂不可用）"


async def _load_knowledge_context(query: str) -> str:
    """从 RAG 知识库获取医学知识（复用 SyncHealth 的 Dify）"""
    # 这里复用 MCP 或直接调用 Dify
    # 暂时返回空，后续在 tools/knowledge.py 中实现
    try:
        from app.tools.knowledge import search_medical_knowledge
        result = await search_medical_knowledge.ainvoke({"query": query})
        if result and result.strip():
            return f"## 医学知识参考\n{result}"
        return ""
    except Exception as e:
        logger.warning(f"知识检索失败，降级为空: {e}")
        return ""
