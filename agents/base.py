"""
BaseAgent is a simple wrapper around an AI provider that allows you
to send messages and receive responses as dictionaries. It handles the
initialization and cleanup of the AI provider session, and provides a
convenient interface for querying the agent.
"""

import json
from contextlib import AsyncExitStack

from ai_providers import AIProviderConfig, BaseAIProvider, managed_ai_provider


class JSONParseError(Exception):
    """Raised when the AI fails to return valid JSON after all retries."""


class BaseAgent:
    """Base class for agents that interact with AI providers."""

    def __init__(self, config: AIProviderConfig):
        self._config = config
        self._provider: BaseAIProvider | None = None
        self._exit_stack = None

    async def __aenter__(self):
        self._exit_stack = AsyncExitStack()
        self._provider = await self._exit_stack.enter_async_context(
            managed_ai_provider(self._config)
        )
        await self._provider.initialize_session()
        return self

    async def __aexit__(self, *args):
        if self._exit_stack is not None:
            await self._exit_stack.__aexit__(*args)
        self._provider = None
        self._exit_stack = None

    async def query(self, user_message: str) -> str:
        """Sends a message to the agent and returns the raw response string."""

        if self._provider is None:
            raise RuntimeError("Agent is not initialized. Use async with.")

        return await self._provider.send_message_and_await_response(user_message)

    async def query_json(self, user_message: str, max_retries: int = 3) -> dict:
        """Sends a message to the agent and returns the response parsed as a dictionary.

        If the response is not valid JSON, sends the parse error back to the provider
        and retries up to max_retries times. Raises JSONParseError on exhaustion.
        """

        raw = await self.query(user_message)

        for attempt in range(max_retries + 1):
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                if attempt == max_retries:
                    raise JSONParseError(
                        f"Failed to parse JSON after {max_retries + 1} attempts. "
                        f"Last error: {exc}. Last response: {raw!r}"
                    ) from exc

                raw = await self.query(
                    f"Your previous response could not be parsed as JSON.\n"
                    f"Error: {exc}\n"
                    f"Response received: {raw!r}\n\n"
                    f"Please respond with valid JSON only — no explanation," +
                    "no markdown, no code fences."
                )

        return {}
