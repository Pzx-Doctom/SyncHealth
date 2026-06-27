"""ChromaDB 向量存储 - 长期记忆的语义检索基础"""
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

# 全局 ChromaDB 客户端和集合
_chroma_client = None
_health_events_collection = None
_embedding_fn = None


def init_vector_store():
    """初始化 ChromaDB 向量存储"""
    global _chroma_client, _health_events_collection, _embedding_fn

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

        # 初始化嵌入函数
        if settings.EMBEDDING_API_KEY:
            _embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.EMBEDDING_API_KEY,
                api_base=settings.EMBEDDING_BASE_URL,
                model_name=settings.EMBEDDING_MODEL,
            )
        else:
            # 降级：尝试使用默认的 sentence-transformers
            try:
                _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except Exception as st_err:
                logger.warning(
                    f"sentence-transformers 不可用 ({st_err})，"
                    f"长期记忆向量检索将禁用。如需启用请配置 EMBEDDING_API_KEY 或安装 sentence_transformers。"
                )
                _embedding_fn = None

        # 创建或获取健康事件集合（仅当嵌入函数可用时）
        if _embedding_fn is not None:
            _health_events_collection = _chroma_client.get_or_create_collection(
                name="health_events",
                embedding_function=_embedding_fn,
                metadata={"description": "用户健康事件长期记忆"},
            )
            logger.info(f"ChromaDB 初始化完成，路径: {settings.CHROMA_PERSIST_DIR}")
        else:
            _chroma_client = None
            _health_events_collection = None

    except Exception as e:
        logger.error(f"ChromaDB 初始化失败: {e}")
        # 降级模式：不使用向量存储
        _chroma_client = None
        _health_events_collection = None


def is_available() -> bool:
    """检查向量存储是否可用"""
    return _health_events_collection is not None


async def add_health_event(
    user_id: str,
    summary: str,
    event_type: str = "health_event",
    details: Optional[dict] = None,
    source_agent: Optional[str] = None,
) -> str:
    """
    添加健康事件到向量存储。
    返回事件 ID。
    """
    if not is_available():
        logger.warning("向量存储不可用，跳过事件存储")
        return ""

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    metadata = {
        "user_id": user_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "source_agent": source_agent or "unknown",
    }
    if details:
        # ChromaDB metadata 只支持基础类型
        import json
        metadata["details"] = json.dumps(details, ensure_ascii=False)

    try:
        _health_events_collection.add(
            ids=[event_id],
            documents=[summary],
            metadatas=[metadata],
        )
        logger.info(f"健康事件已存储: {event_id} ({event_type})")
        return event_id
    except Exception as e:
        logger.error(f"健康事件存储失败: {e}")
        return ""


async def search_health_events(
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    语义搜索用户的健康事件。
    返回最相关的事件列表。
    """
    if not is_available():
        logger.warning("向量存储不可用，返回空结果")
        return []

    try:
        results = _health_events_collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"user_id": user_id},
        )

        events = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                # 距离转相似度（ChromaDB 默认余弦距离）
                similarity = 1 - distance if distance <= 1 else 0

                import json
                details = {}
                if meta.get("details"):
                    try:
                        details = json.loads(meta["details"])
                    except json.JSONDecodeError:
                        pass

                events.append({
                    "id": results["ids"][0][i],
                    "summary": doc,
                    "event_type": meta.get("event_type", "event"),
                    "timestamp": meta.get("timestamp", ""),
                    "similarity": similarity,
                    "details": details,
                    "source_agent": meta.get("source_agent"),
                })

        return events

    except Exception as e:
        logger.error(f"健康事件搜索失败: {e}")
        return []


async def get_user_timeline(
    user_id: str,
    limit: int = 20,
) -> list[dict]:
    """
    获取用户健康事件时间线（按时间倒序）。
    """
    if not is_available():
        return []

    try:
        # ChromaDB 不直接支持 ORDER BY，先获取全部再排序
        results = _health_events_collection.get(
            where={"user_id": user_id},
            limit=limit * 2,  # 多取一些再排序
        )

        events = []
        if results and results.get("documents"):
            import json
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i]
                details = {}
                if meta.get("details"):
                    try:
                        details = json.loads(meta["details"])
                    except json.JSONDecodeError:
                        pass

                events.append({
                    "id": results["ids"][i],
                    "summary": doc,
                    "event_type": meta.get("event_type", "event"),
                    "timestamp": meta.get("timestamp", ""),
                    "details": details,
                })

        # 按时间倒序排序
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events[:limit]

    except Exception as e:
        logger.error(f"时间线获取失败: {e}")
        return []
