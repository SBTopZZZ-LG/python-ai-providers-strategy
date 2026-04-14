"""Main module to demonstrate usage of the AI provider framework."""

import asyncio
from typing import Any

from ai_providers import AIProviderConfig, BaseTool, ProviderType, managed_ai_provider


async def _ping_handler(invocation: dict[str, Any]) -> dict[str, Any]:  # noqa: RUF029
    """Echo the ping value back as a pong."""
    value = invocation.get("arguments", {}).get("value", "")
    return {
        "textResultForLlm": f"pong: {value}",
        "resultType": "success",
        "sessionLog": f"ping_pong called with value={value!r}",
    }


async def main():
    """Main function to demonstrate usage of the AI provider framework."""

    print("Initializing configuration...")
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",  # or gpt-5
        system_prompt="You are a helpful assistant.",
        timeout=120,  # 2 minutes
        tools=[
            BaseTool(
                name="ping_pong",
                description="Echoes back the provided value as a pong response.",
                parameters={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                            "description": "The value to echo back.",
                        },
                    },
                    "required": ["value"],
                },
                handler=_ping_handler,
            )
        ],
    )

    try:
        async with managed_ai_provider(config) as provider:
            print("Initializing session...")
            await provider.initialize_session()

            print("Sending message...")
            question = "Can you give me a 2-sentence summary of the MCP protocol?"
            print(f"Question: {question}")

            response = await provider.send_message_and_await_response(question)

            print("\nResponse:")
            print("-" * 20)
            print(response)
            print("-" * 20)
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
