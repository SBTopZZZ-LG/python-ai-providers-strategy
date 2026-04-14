import asyncio

from ai_providers import AIProviderConfig, ProviderType, create_ai_provider, dispose_ai_provider


async def main():
    print("Initializing configuration...")
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",  # or gpt-5
        timeout=120 # 2 minutes
    )

    # 1. Create the provider using the factory
    provider = await create_ai_provider(config)

    try:
        # 2. Initialize the session
        print("Initializing session...")
        # Note: If CopilotClient needs an explicit connect() before getting state 'connected',
        # it might need to be handled in the factory or provider.
        await provider.initialize_session()

        # 3. Send a test message
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
    finally:
        # 4. Clean up
        print("Disposing session...")
        await dispose_ai_provider(provider)

if __name__ == "__main__":
    asyncio.run(main())
