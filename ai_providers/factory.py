"""Factory for creating AI provider instances based on a generic configuration."""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from enum import Enum

from .base import BaseAIProvider
from .copilot import CopilotProvider, CopilotProviderOptions


class ProviderType(Enum):
    """Enum for supported AI provider types."""

    COPILOT = "copilot"


@dataclass
class AIProviderConfig:
    """Generic configuration provided by the caller to initialize the requested AI provider."""

    provider_type: ProviderType

    model: str = "gpt-4o"
    timeout: float = 1800


async def create_ai_provider(config: AIProviderConfig) -> BaseAIProvider:
    """
    Factory method to create an AI provider instance mapped from a generic config object.
    The caller doesn't need to know the specific options dataclass required by the provider.
    """

    if config.provider_type == ProviderType.COPILOT:
        import copilot

        async with AsyncExitStack() as stack:
            client = copilot.CopilotClient()

            try:
                await client.start()
            except Exception as e:
                raise RuntimeError(f"Failed to start Copilot client: {str(e)}") from e

            stack.push_async_callback(client.stop)

            options = CopilotProviderOptions(
                client=client,
                model=config.model,
                timeout=config.timeout
            )
            provider = CopilotProvider(options)

            stack.pop_all()
            return provider

    raise ValueError(f"Unknown provider type: {config.provider_type}")

async def dispose_ai_provider(provider: BaseAIProvider):
    """Factory method to dispose of an AI provider instance."""

    async with AsyncExitStack() as stack:
        if isinstance(provider, CopilotProvider):
            copilot_provider_client = provider.options.client
            if copilot_provider_client is not None:
                stack.push_async_callback(copilot_provider_client.stop)
        else:
            raise ValueError(f"Unknown provider type: {type(provider)}")

        stack.push_async_callback(provider.dispose_session)


@asynccontextmanager
async def managed_ai_provider(config: AIProviderConfig):
    provider = await create_ai_provider(config)
    try:
        yield provider
    finally:
        await dispose_ai_provider(provider)
