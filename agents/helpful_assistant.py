"""HelpfulAssistantAgent definition."""

from tools.ping_pong import make_prefixed_ping_pong_tool, ping_pong

from .base import BaseAgent


class HelpfulAssistantAgent(BaseAgent):
    """A helpful assistant agent with ping-pong tool demonstrations."""

    def __init__(self) -> None:
        system_prompt = "You are a helpful assistant."
        tools = (
            ping_pong,
            make_prefixed_ping_pong_tool(prefix="[HelpfulAssistant]"),
        )

        super().__init__(system_prompt, tools)
