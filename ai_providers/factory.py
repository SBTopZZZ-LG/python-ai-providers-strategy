"""Factory for creating AI provider instances based on a generic configuration."""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseAIProvider, BaseTool
from .copilot import CopilotProvider, CopilotProviderOptions
from .openai import OpenAIProvider, OpenAIProviderOptions


class ProviderType(Enum):
    COPILOT = "copilot"
    OPENAI = "openai"


@dataclass
class AIProviderConfig:
    provider_type: ProviderType
    model: str
    timeout: float
    system_prompt: str = "You are a helpful assistant."
    tools: list[BaseTool] = field(default_factory=list)
    api_key: str = "none"
    base_url: str = "https://api.openai.com/v1"


async def create_ai_provider(config: AIProviderConfig) -> BaseAIProvider:
    if config.provider_type == ProviderType.COPILOT:
        import copilot
        async with AsyncExitStack() as stack:
            client = copilot.CopilotClient()
            try:
                await client.start()
            except Exception as e:
                raise RuntimeError(f"Failed to start Copilot client: {str(e)}") from e
            stack.push_async_callback(client.stop)
            try:
                options = CopilotProviderOptions(
                    client=client,
                    model=config.model,
                    system_prompt=config.system_prompt,
                    timeout=config.timeout,
                    tools=config.tools,
                )
                provider = CopilotProvider(options)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Copilot provider: {str(e)}") from e
            stack.pop_all()
            return provider

    if config.provider_type == ProviderType.OPENAI:
        options = OpenAIProviderOptions(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            system_prompt=config.system_prompt,
            timeout=config.timeout,
            tools=config.tools,
        )
        return OpenAIProvider(options)

    raise ValueError(f"Unknown provider type: {config.provider_type}")


async def dispose_ai_provider(provider: BaseAIProvider):
    try:
        async with AsyncExitStack() as stack:
            if isinstance(provider, CopilotProvider):
                copilot_provider_client = provider.options.client
                if copilot_provider_client is not None:
                    stack.push_async_callback(copilot_provider_client.stop)
            stack.push_async_callback(provider.dispose_session)
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to dispose AI provider: {str(e)}") from e


@asynccontextmanager
async def managed_ai_provider(config: AIProviderConfig):
    provider = await create_ai_provider(config)
    try:
        await provider.initialize_session()
        yield provider
    finally:
        await dispose_ai_provider(provider)