"""OpenAI AI provider implementation."""

import json
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from .base import BaseAIProvider, BaseAIProviderOptions, BaseTool


@dataclass
class OpenAIProviderOptions(BaseAIProviderOptions):
    api_key: str = "none"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    system_prompt: str = "You are a helpful assistant."
    timeout: float = 60.0
    tools: list[BaseTool] = field(default_factory=list)


class OpenAIProvider(BaseAIProvider[OpenAIProviderOptions]):
    def __init__(self, options: OpenAIProviderOptions):
        super().__init__(options)
        self._client = AsyncOpenAI(
            api_key=options.api_key,
            base_url=options.base_url,
            timeout=options.timeout,
        )
        self._messages: list[dict[str, Any]] = []

    async def initialize_session(self):
        self._messages = [
            {"role": "system", "content": self.options.system_prompt}
        ]

    async def send_message_and_await_response(self, message: str) -> str:
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
            msg = response.choices[0].message

            if msg.tool_calls:
                self._messages.append({"role": "assistant", "content": msg.content or ""})
                for tc in msg.tool_calls:
                    tc_id = tc.id or ""
                    tc_name = tc.function.name or ""
                    tc_args = json.loads(tc.function.arguments or "{}")
                    result = self.options.tools[
                        next(i for i, t in enumerate(self.options.tools) if t.name == tc_name)
                    ].handler(
                        {
                            "session_id": "",
                            "tool_call_id": tc_id,
                            "tool_name": tc_name,
                            "arguments": tc_args,
                        }
                    )
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
        self._messages = []