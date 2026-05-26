"""Base class for agent definitions."""

from abc import ABC

from ai_providers import BaseTool


class BaseAgent(ABC):
    """Base class for agent definitions.

    Subclasses declare the agent's identity as class-level attributes.
    Callers pass these to :class:`~ai_providers.AIProviderConfig` when
    constructing a provider session.
    """

    _system_prompt: str
    _tools: tuple[BaseTool, ...]

    def __init__(self, system_prompt: str, tools: tuple[BaseTool, ...]) -> None:
        self._system_prompt = system_prompt
        self._tools = tools

    def get_system_prompt(self) -> str:
        """Gets the system prompt for the Agent."""
        return self._system_prompt

    def get_tools(self) -> tuple[BaseTool, ...]:
        """Gets the tuple of tools for the Agent."""
        return self._tools
