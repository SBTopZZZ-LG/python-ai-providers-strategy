"""
HelpfulAssistantAgent is a simple agent that demonstrates
how to use the AI provider framework. It sets a system prompt
to establish a helpful assistant persona, and inherits the
querying and JSON parsing capabilities from BaseAgent.

This agent can be used as a starting point for building more
complex agents with additional tools and capabilities.
"""


from ai_providers import AIProviderConfig

from tools.ping_pong import ping_pong, make_prefixed_ping_pong_tool

from .base import BaseAgent


_SYSTEM_PROMPT = """You are a helpful assistant."""


class HelpfulAssistantAgent(BaseAgent):
    """
    HelpfulAssistantAgent is a simple agent that demonstrates
    how to use the AI provider framework.
    """

    def __init__(self, config: AIProviderConfig):
        config.system_prompt = _SYSTEM_PROMPT
        config.tools = [
            ping_pong,
            make_prefixed_ping_pong_tool(prefix="[HelpfulAssistant]"),
        ]
        super().__init__(config)
