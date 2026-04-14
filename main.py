"""Main module to demonstrate usage of the AI provider framework."""

import asyncio

from ai_providers import AIProviderConfig, ProviderType, managed_ai_provider


async def main():
    """Main function to demonstrate usage of the AI provider framework."""

    print("Initializing configuration...")
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",  # or gpt-5
        timeout=120  # 2 minutes
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
