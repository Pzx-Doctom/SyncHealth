"""Agent 基础类 + 共享 LLM 实例"""
import functools
import json
import re
from typing import Any, Optional

import httpx
from langchain_openai import ChatOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.core.errors import LLMCallError, JSONParseError


_llm_instance: Optional[ChatOpenAI] = None
_vision_llm_instance: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """获取 LLM 单例（复用 DeepSeek / OpenAI 兼容 API）"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            model=settings.AI_MODEL,
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            temperature=settings.AI_TEMPERATURE,
            timeout=60,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    return _llm_instance


def get_vision_llm() -> ChatOpenAI:
    """获取多模态 LLM 单例（用于 OCR）"""
    global _vision_llm_instance
    if _vision_llm_instance is None:
        _vision_llm_instance = ChatOpenAI(
            model=settings.VISION_MODEL,
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            temperature=0.2,  # OCR 需要更低温度
            timeout=60,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    return _vision_llm_instance


@retry(
    stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, LLMCallError)),
    reraise=True,
)
async def safe_llm_call(llm: ChatOpenAI, messages: list) -> Any:
    """
    带指数退避的 LLM 调用。
    重试策略：3 次，退避 1s → 2s → 4s
    """
    try:
        return await llm.ainvoke(messages)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise LLMCallError(f"LLM 限流: {e}", provider=settings.AI_PROVIDER)
        raise LLMCallError(f"LLM HTTP 错误 {e.response.status_code}: {e}", provider=settings.AI_PROVIDER)
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        raise LLMCallError(f"LLM 网络错误: {e}", provider=settings.AI_PROVIDER)


async def safe_tool_call(tool_func, *args, timeout: int = None, tool_name: str = None, **kwargs) -> Any:
    """
    带超时的工具调用。
    超时或异常时返回错误 JSON 字符串（而非抛异常），让 Agent 能继续推理。
    """
    import asyncio
    import json as _json

    actual_timeout = timeout or settings.TOOL_TIMEOUT_SECONDS
    name = tool_name or getattr(tool_func, 'name', 'unknown')

    try:
        result = await asyncio.wait_for(tool_func(*args, **kwargs), timeout=actual_timeout)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"工具 {name} 执行超时({actual_timeout}s)，返回降级结果")
        return _json.dumps({
            "error": f"工具 {name} 执行超时({actual_timeout}s)",
            "fallback": "数据暂时不可用，请基于已有信息继续分析",
        }, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"工具 {name} 执行异常: {e}，返回降级结果")
        return _json.dumps({
            "error": f"工具 {name} 执行失败: {e}",
            "fallback": "数据暂时不可用，请基于已有信息继续分析",
        }, ensure_ascii=False)


def parse_json_response(text: str, fallback: Optional[dict] = None) -> dict:
    """
    带降级的 JSON 解析。
    1. 尝试直接 json.loads
    2. 尝试从 markdown 代码块提取
    3. 尝试正则提取 JSON 对象
    4. 返回 fallback
    """
    if not text:
        return fallback or {}

    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 从 markdown 代码块提取
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 正则提取最外层 { ... }
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. 兜底
    return fallback or {}


def append_route(state: dict, from_agent: str, to_agent: str, reason: str) -> list:
    """追加 Agent 路由事件到 agent_route 列表"""
    from datetime import datetime, timezone
    new_route = {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return state.get("agent_route", []) + [new_route]


def increment_loop(state: dict) -> int:
    """递增循环计数器"""
    return state.get("loop_count", 0) + 1


def extract_tool_calls_from_messages(messages: list, agent_name: str) -> list[dict]:
    """
    从 create_react_agent 的结果消息中提取工具调用记录。
    遍历消息列表，配对 AIMessage 的 tool_calls 与 ToolMessage 的结果。
    """
    from datetime import datetime, timezone

    records: list[dict] = []
    pending_calls: dict[str, dict] = {}  # tool_call_id -> {tool, args}

    for msg in messages:
        # AIMessage 携带 tool_calls（函数调用请求）
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                pending_calls[tc_id] = {
                    "tool": tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown"),
                    "args": tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {}),
                }

        # ToolMessage 携带工具执行结果
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool":
            tc_id = getattr(msg, "tool_call_id", "")
            call_info = pending_calls.pop(
                tc_id,
                {"tool": getattr(msg, "name", "unknown"), "args": {}},
            )
            records.append({
                "agent": agent_name,
                "tool": call_info["tool"],
                "args": call_info["args"] if isinstance(call_info["args"], dict) else {"input": str(call_info["args"])},
                "result": str(getattr(msg, "content", ""))[:500],
                "status": "success",
                "duration_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    return records
