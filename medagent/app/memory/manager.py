"""HealthMemoryManager - 统一管理长期记忆的三个组成部分"""
import logging
from datetime import datetime, timezone
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.memory import vector_store
from app.memory.profile import get_profile, update_profile

logger = logging.getLogger(__name__)


class _SimpleSummaryMemory:
    """
    轻量级摘要记忆（替代 LangChain 1.x 已移除的 ConversationSummaryBufferMemory）。
    维护对话历史，超过 token 阈值时用 LLM 压缩为摘要。
    """

    SUMMARY_PROMPT = (
        "请将以下对话历史压缩为简洁的摘要，保留关键健康信息、症状、用药、建议等要点：\n\n"
    )

    def __init__(self, llm, max_token_count: int = 2000):
        self._llm = llm
        self._max_tokens = max_token_count
        self._buffer: list = []       # 当前对话消息
        self._summary: str = ""       # 压缩后的摘要

    @property
    def buffer(self):
        """返回当前摘要 + 缓冲区内容"""
        if self._summary:
            return [SystemMessage(content=f"对话历史摘要: {self._summary}")] + self._buffer
        return self._buffer

    def save_context(self, inputs: dict, outputs: dict):
        """添加一轮对话"""
        self._buffer.append(HumanMessage(content=inputs.get("input", "")))
        self._buffer.append(AIMessage(content=outputs.get("output", "")))
        self._maybe_summarize()

    def _maybe_summarize(self):
        """超过阈值时触发摘要"""
        # 粗略估算：每条消息约 50 token，超过阈值 2/3 时压缩
        threshold_msgs = (self._max_tokens // 50) * 2 // 3
        if len(self._buffer) <= threshold_msgs:
            return

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在事件循环中，跳过同步摘要（稍后异步处理）
                return
            self._do_summarize()
        except RuntimeError:
            self._do_summarize()

    def _do_summarize(self):
        """执行同步摘要"""
        try:
            history_text = "\n".join(
                f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content}"
                for m in self._buffer
            )
            messages = [
                SystemMessage(content=self.SUMMARY_PROMPT),
                HumanMessage(content=history_text),
            ]
            resp = self._llm.invoke(messages)
            new_summary = resp.content
            # 合并旧摘要
            if self._summary:
                new_summary = f"{self._summary}\n{new_summary}"
            self._summary = new_summary
            self._buffer = []  # 清空缓冲区
        except Exception as e:
            logger.warning(f"对话摘要生成失败，保留原始缓冲: {e}")


class HealthMemoryManager:
    """
    长期记忆管理器，包含三部分：
    1. 用户画像（关系型存储，UserProfile 表）
    2. 对话摘要缓冲区（ConversationSummaryBufferMemory）
    3. 健康事件向量存储（ChromaDB，语义检索）
    """

    def __init__(self):
        self._summary_memories: dict[str, ConversationSummaryBufferMemory] = {}

    def _get_summary_memory(self, user_id: str) -> _SimpleSummaryMemory:
        """获取用户的对话摘要记忆（按用户隔离）"""
        if user_id not in self._summary_memories:
            llm = ChatOpenAI(
                model=settings.AI_MODEL,
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
                temperature=0.3,
                max_retries=2,
            )
            self._summary_memories[user_id] = _SimpleSummaryMemory(
                llm=llm,
                max_token_count=2000,
            )
        return self._summary_memories[user_id]

    async def get_profile(self, user_id: str) -> Optional[dict]:
        """获取用户健康画像"""
        return await get_profile(user_id)

    async def update_profile(self, user_id: str, profile_data: dict) -> dict:
        """更新用户画像"""
        return await update_profile(user_id, profile_data)

    async def recall(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        语义检索用户的长期记忆（健康事件）。
        返回与查询最相关的历史事件。
        """
        return await vector_store.search_health_events(user_id, query, top_k)

    async def remember(
        self,
        user_id: str,
        summary: str,
        event_type: str = "health_event",
        details: Optional[dict] = None,
        source_agent: Optional[str] = None,
    ) -> str:
        """
        将重要事件存入长期记忆（向量存储）。
        应在对话结束后自动提取关键事件并存储。
        """
        return await vector_store.add_health_event(
            user_id=user_id,
            summary=summary,
            event_type=event_type,
            details=details,
            source_agent=source_agent,
        )

    def get_conversation_summary(self, user_id: str) -> str:
        """获取当前对话摘要"""
        memory = self._get_summary_memory(user_id)
        buffer = memory.buffer
        if isinstance(buffer, str):
            return buffer
        # 如果是消息列表，取最后一条的 content
        if buffer and hasattr(buffer[-1], "content"):
            return buffer[-1].content
        return ""

    def add_to_conversation(self, user_id: str, human_msg: str, ai_msg: str):
        """添加一轮对话到摘要记忆"""
        memory = self._get_summary_memory(user_id)
        memory.save_context(
            {"input": human_msg},
            {"output": ai_msg},
        )

    async def get_timeline(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取用户健康事件时间线"""
        return await vector_store.get_user_timeline(user_id, limit)

    async def extract_and_store_events(
        self,
        user_id: str,
        user_query: str,
        ai_response: str,
        agent_route: list[dict],
        tool_calls: list[dict],
    ) -> list[str]:
        """
        从对话中提取关键健康事件并存入长期记忆。
        在每轮对话结束后调用。
        """
        stored_ids = []

        try:
            # 如果涉及用药，记录用药变更
            for tc in tool_calls:
                if tc.get("tool") == "create_medication_reminder":
                    drug = tc.get("args", {}).get("drug_name", "未知药品")
                    event_id = await self.remember(
                        user_id=user_id,
                        summary=f"用户开始用药: {drug}",
                        event_type="medication_change",
                        details=tc.get("args", {}),
                        source_agent=tc.get("agent"),
                    )
                    if event_id:
                        stored_ids.append(event_id)

                elif tc.get("tool") == "ocr_medical_report":
                    event_id = await self.remember(
                        user_id=user_id,
                        summary=f"用户上传了体检报告并解读",
                        event_type="health_event",
                        details={"query": user_query[:100]},
                        source_agent="report_interpreter",
                    )
                    if event_id:
                        stored_ids.append(event_id)

                elif tc.get("tool") == "ocr_medicine_box":
                    event_id = await self.remember(
                        user_id=user_id,
                        summary=f"用户查询了药品信息",
                        event_type="medication_change",
                        details={"query": user_query[:100]},
                        source_agent="medication",
                    )
                    if event_id:
                        stored_ids.append(event_id)

            # 将对话添加到摘要记忆
            self.add_to_conversation(user_id, user_query, ai_response)

        except Exception as e:
            logger.error(f"事件提取存储失败: {e}")

        return stored_ids


# 全局单例
memory_manager = HealthMemoryManager()
