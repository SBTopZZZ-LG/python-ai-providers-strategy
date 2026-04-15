"""Main module to demonstrate usage of the AI provider framework."""

import asyncio

from agents import HelpfulAssistantAgent
from ai_providers import AIProviderConfig, ProviderType


async def main():
    """Main function to demonstrate usage of the AI provider framework."""

    print("Initializing configuration...")
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4.1",  # or gpt-5
        timeout=120,  # 2 minutes
    )

    try:
        async with HelpfulAssistantAgent(config) as agent:
            print("Sending message...")
            question = "Can you give me a 2-sentence summary of the MCP protocol?"
            print(f"Question: {question}")

            response = await agent.query(question)

            print("\nResponse:")
            print("-" * 20)
            print(response)
            print("-" * 20)
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
