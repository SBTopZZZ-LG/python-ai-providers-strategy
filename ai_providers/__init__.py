"""AI Providers package."""

from .base import BaseAIProvider, BaseAIProviderOptions, \
    BaseTool, ToolHandler, ToolInvocation, ToolResult, ToolResultType
from .copilot import CopilotProvider, CopilotProviderOptions
from .factory import AIProviderConfig, ProviderType, \
    create_ai_provider, dispose_ai_provider, managed_ai_provider

__all__ = [
    "AIProviderConfig",
    "BaseAIProvider",
    "BaseAIProviderOptions",
    "BaseTool",
    "CopilotProvider",
    "CopilotProviderOptions",
    "ProviderType",
    "ToolHandler",
    "ToolInvocation",
    "ToolResult",
    "ToolResultType",
    "create_ai_provider",
    "dispose_ai_provider",
    "managed_ai_provider"
]
