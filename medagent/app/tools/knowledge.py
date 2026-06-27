"""RAG 医学知识检索工具 - 复用 SyncHealth 的 Dify 知识库"""
import json
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agents.base import safe_tool_call

logger = logging.getLogger(__name__)


class KnowledgeInput(BaseModel):
    query: str = Field(description="搜索关键词")


@tool(args_schema=KnowledgeInput)
async def search_medical_knowledge(query: str) -> str:
    """
    搜索医学知识库获取相关参考信息。
    覆盖症状、疾病、药品、检查指标等领域。
    数据来源：SyncHealth Dify 知识库（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "search_medical_knowledge", {"query": query}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="search_medical_knowledge")


@tool(args_schema=KnowledgeInput)
async def search_fitness_knowledge(query: str) -> str:
    """
    搜索运动健康知识库，获取运动、睡眠、营养等方面的专业指导。
    数据来源：SyncHealth Dify 知识库（通过 MCP）。
    """
    async def _execute() -> str:
        from app.mcp.client import mcp_client
        return await mcp_client.call_health_tool(
            "search_fitness_knowledge", {"query": query}
        )
    return await safe_tool_call(_execute, timeout=30, tool_name="search_fitness_knowledge")
