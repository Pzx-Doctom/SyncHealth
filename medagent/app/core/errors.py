"""MedAgent Hub 自定义异常"""
from typing import Optional


class MedAgentError(Exception):
    """MedAgent Hub 基础异常"""
    def __init__(self, message: str, error_type: str = "generic", recoverable: bool = False):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.recoverable = recoverable


class LLMCallError(MedAgentError):
    """LLM 调用失败"""
    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, error_type="llm_error", recoverable=True)
        self.provider = provider


class ToolExecutionError(MedAgentError):
    """工具执行失败"""
    def __init__(self, message: str, tool_name: str = ""):
        super().__init__(message, error_type="tool_error", recoverable=True)
        self.tool_name = tool_name


class ToolTimeoutError(MedAgentError):
    """工具执行超时"""
    def __init__(self, message: str, tool_name: str = ""):
        super().__init__(message, error_type="tool_timeout", recoverable=True)
        self.tool_name = tool_name


class MCPConnectionError(MedAgentError):
    """MCP 连接失败"""
    def __init__(self, message: str):
        super().__init__(message, error_type="mcp_error", recoverable=True)


class JSONParseError(MedAgentError):
    """JSON 解析失败"""
    def __init__(self, message: str, raw_text: str = ""):
        super().__init__(message, error_type="json_parse_error", recoverable=True)
        self.raw_text = raw_text


class LoopLimitExceeded(MedAgentError):
    """循环路由超限"""
    def __init__(self, message: str = "Agent 路由循环超过上限"):
        super().__init__(message, error_type="loop_limit", recoverable=False)
