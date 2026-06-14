"""OpenAI AI provider implementation."""

import inspect
import json
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from .base import BaseAIProvider, BaseAIProviderOptions, BaseTool


@dataclass
class OpenAIProviderOptions(BaseAIProviderOptions):
    """Options for initializing the OpenAI provider.

    Attributes:
        api_key: API key for authenticating with the OpenAI API.
        base_url: Base URL for the OpenAI API endpoint.
        model: Model identifier used for chat completions.
        system_prompt: System prompt passed to the model as the initial system message.
        timeout: Timeout in seconds for API requests.
        tools: Provider-agnostic tool definitions registered with the session.
            Each ``BaseTool`` is formatted as an OpenAI function tool at request time.
    """

    api_key: str = "none"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    system_prompt: str = "You are a helpful assistant."
    timeout: float = 60.0
    tools: list[BaseTool] = field(default_factory=list)


class OpenAIProvider(BaseAIProvider[OpenAIProviderOptions]):
    """OpenAI AI provider implementation.

    Args:
        options: OpenAI provider options including api_key, base_url, model,
            system_prompt, timeout, and tools.
    """

    _client: AsyncOpenAI
    _messages: list[dict[str, Any]]

    def __init__(self, options: OpenAIProviderOptions):
        """Initialize the OpenAI provider.

        Args:
            options: OpenAI provider options.
        """

        super().__init__(options)
        self._client = AsyncOpenAI(
            api_key=options.api_key,
            base_url=options.base_url,
            timeout=options.timeout,
        )
        self._messages = []

    async def initialize_session(self):
        """Initialize the message history for an OpenAI chat session.

        Sets up the initial system message from the configured system prompt.

        Returns:
            None

        Raises:
            ValueError: If model or timeout configuration is invalid.
        """

        options = self.options

        if options.model is None or str.strip(options.model) == "":
            raise ValueError(
                "Valid model name must be provided for session initialization."
            )
        if options.timeout <= 0:
            raise ValueError(
                "Timeout must be a positive floating point number for session initialization."
            )

        if self._messages:
            print(
                "Warning: OpenAI session already initialized. Reinitializing session."
            )
            await self.dispose_session()

        self._messages = [{"role": "system", "content": options.system_prompt}]

    async def send_message_and_await_response(self, message: str) -> str:
        """Send a prompt and wait for an OpenAI response.

        Handles tool call loops automatically: when the model requests tool
        invocations, the corresponding handlers are called and results are
        fed back until the model produces a final text response.

        Args:
            message: Prompt content to send to the active session.

        Returns:
            Response content text. Returns an empty string when no content is present.

        Raises:
            ValueError: If no session is initialized.
            RuntimeError: If the API returns an invalid or empty response.
        """

        if not self._messages:
            raise ValueError("OpenAI session is not initialized.")

        self._messages.append({"role": "user", "content": message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.options.tools
        ]

        while True:
            kwargs: dict[str, Any] = {
                "model": self.options.model,
                "messages": self._messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self._client.chat.completions.create(**kwargs)

            if response is None or not response.choices:
                raise RuntimeError("Received empty response from OpenAI API.")

            msg = response.choices[0].message

            if msg.tool_calls:
                self._messages.append(
                    {"role": "assistant", "content": msg.content or ""}
                )
                for tc in msg.tool_calls:
                    tc_id = tc.id or ""
                    tc_name = tc.function.name or ""
                    tc_args = json.loads(tc.function.arguments or "{}")
                    result = self.options.tools[
                        next(
                            i
                            for i, t in enumerate(self.options.tools)
                            if t.name == tc_name
                        )
                    ].handler(
                        {
                            "session_id": "",
                            "tool_call_id": tc_id,
                            "tool_name": tc_name,
                            "arguments": tc_args,
                        }
                    )
                    if inspect.isawaitable(result):
                        result = await result

                    self._messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result.get("textResultForLlm", ""),
                        }
                    )
                continue

            assistant_content = msg.content or ""
            self._messages.append({"role": "assistant", "content": assistant_content})
            return assistant_content

    async def dispose_session(self):
        """Dispose the active OpenAI session by clearing message history.

        Returns:
            None
        """

        self._messages = []
