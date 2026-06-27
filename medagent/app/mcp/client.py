"""MCP 客户端 - 连接 SyncHealth backend 获取健康数据"""
import json
import logging
from typing import Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.core.errors import MCPConnectionError

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP 客户端 - 通过 HTTP 连接 SyncHealth backend 的 MCP 端点。
    支持重连和降级机制。
    """

    def __init__(self):
        self.base_url = settings.SYNCHEALTH_BASE_URL
        self.token = settings.SYNCHEALTH_MCP_TOKEN
        self._client: Optional[httpx.AsyncClient] = None
        self._available = False
        self._fallback_cache: dict[str, str] = {}  # 降级时的本地缓存

    async def warmup(self):
        """预热连接（在应用启动时调用）"""
        try:
            await self._ensure_client()
            # 简单的健康检查
            resp = await self._client.get(
                f"{self.base_url}/api/v1/mcp/health",
                timeout=5,
            )
            self._available = resp.status_code == 200
            if self._available:
                logger.info("MCP 连接预热成功")
            else:
                logger.warning(f"MCP 健康检查失败: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"MCP 预热失败，进入降级模式: {e}")
            self._available = False

    async def _ensure_client(self):
        """确保 HTTP 客户端可用"""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=10,
            )

    @retry(
        stop=stop_after_attempt(settings.MCP_RECONNECT_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _call_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带重试的 HTTP 调用"""
        await self._ensure_client()
        return await self._client.request(method, url, **kwargs)

    async def get_health_context(self, user_id: str, query: str) -> str:
        """
        获取用户的健康数据上下文。
        如果 MCP 不可用，降级到本地缓存或返回提示信息。
        """
        try:
            resp = await self._call_with_retry(
                "POST",
                "/api/v1/mcp/health-context",
                json={"user_id": user_id, "query": query},
            )
            if resp.status_code == 200:
                data = resp.json()
                context = data.get("context", "")
                self._fallback_cache[user_id] = context  # 缓存成功结果
                self._available = True
                return context
            else:
                logger.warning(f"MCP 获取健康上下文失败: HTTP {resp.status_code}")
                return self._get_fallback(user_id)
        except Exception as e:
            logger.warning(f"MCP 健康上下文获取异常，降级: {e}")
            self._available = False
            return self._get_fallback(user_id)

    async def call_health_tool(self, tool_name: str, args: dict) -> str:
        """
        调用 SyncHealth 暴露的健康数据工具。
        如果 MCP 不可用，返回降级提示。
        """
        try:
            resp = await self._call_with_retry(
                "POST",
                "/api/v1/mcp/tools/call",
                json={"tool_name": tool_name, "arguments": args},
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", "")
                self._available = True
                return result
            else:
                logger.warning(f"MCP 工具调用失败 {tool_name}: HTTP {resp.status_code}")
                return json.dumps({
                    "error": f"健康数据工具 '{tool_name}' 暂时不可用",
                    "fallback": "请稍后重试，或联系系统管理员",
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"MCP 工具调用异常 {tool_name}: {e}")
            self._available = False
            return json.dumps({
                "error": f"无法连接 SyncHealth 获取 '{tool_name}' 数据",
                "fallback": "健康数据服务暂时不可用，建议稍后重试",
            }, ensure_ascii=False)

    async def list_tools(self) -> list[dict]:
        """获取 MCP 暴露的工具列表"""
        try:
            resp = await self._call_with_retry("GET", "/api/v1/mcp/tools")
            if resp.status_code == 200:
                return resp.json().get("tools", [])
            return []
        except Exception as e:
            logger.warning(f"MCP 工具列表获取失败: {e}")
            return []

    def _get_fallback(self, user_id: str) -> str:
        """获取降级数据（本地缓存）"""
        if user_id in self._fallback_cache:
            return f"## 健康数据（来自缓存，可能非最新）\n{self._fallback_cache[user_id]}"
        return "（SyncHealth 健康数据暂不可用，请稍后重试）"

    @property
    def is_available(self) -> bool:
        """MCP 是否可用"""
        return self._available

    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# 全局单例
mcp_client = MCPClient()
