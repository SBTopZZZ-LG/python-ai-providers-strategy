"""Factory for creating AI provider instances based on a generic configuration."""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseAIProvider, BaseTool
from .openai import OpenAIProvider, OpenAIProviderOptions

try:
    from .copilot import CopilotProvider, CopilotProviderOptions
except ImportError:
    CopilotProvider = None  # type: ignore[assignment,misc]
    CopilotProviderOptions = None  # type: ignore[assignment,misc]


class ProviderType(Enum):
    """Enum for supported AI provider types."""

    COPILOT = "copilot"
    OPENAI = "openai"


@dataclass
class AIProviderConfig:
    """Configuration for AI provider construction and session initialization.

    Attributes:
        provider_type: Provider backend to instantiate.
        model: Model identifier for provider session creation.
        timeout: Timeout in seconds for provider requests.
        system_prompt: System prompt passed to the model at session
            initialization. Defaults to ``"You are a helpful assistant."``.
        tools: Provider-agnostic tool definitions to register with the
            session. Defaults to an empty list (no tools).
        api_key: API key to use against the provider/model.
        base_url: Base url of the provider API.
    """

    provider_type: ProviderType
    model: str
    timeout: float
    system_prompt: str = "You are a helpful assistant."
    tools: list[BaseTool] = field(default_factory=list)
    api_key: str = "none"
    base_url: str = "https://api.openai.com/v1"


async def create_ai_provider(config: AIProviderConfig) -> BaseAIProvider:
    """Create an AI provider instance from a generic configuration.

    Args:
        config: Provider creation settings.

    Returns:
        Initialized provider instance with connected client resources.

    Raises:
        ValueError: If the provider type is unsupported.
        RuntimeError: If provider startup or initialization fails.
    """

    if config.provider_type == ProviderType.COPILOT:
        if CopilotProvider is None:
            raise ValueError(
                "Copilot provider is not available. "
                "Install the 'copilot' package to use this provider."
            )

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
                raise RuntimeError(
                    f"Failed to initialize Copilot provider: {str(e)}"
                ) from e
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
    """Dispose provider-owned resources in reverse lifecycle order.

    Args:
        provider: Provider instance to dispose.

    Returns:
        None

    Raises:
        RuntimeError: If any cleanup step fails.
    """

    try:
        async with AsyncExitStack() as stack:
            if CopilotProvider is not None and isinstance(provider, CopilotProvider):
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
    """Provide a managed provider lifecycle via async context manager.

    Args:
        config: Provider creation settings.

    Yields:
        A created provider instance ready for use.

    Raises:
        ValueError: If the provider type is unsupported.
        RuntimeError: If provider creation or disposal fails.
    """

    provider = await create_ai_provider(config)
    try:
        await provider.initialize_session()
        yield provider
    finally:
        await dispose_ai_provider(provider)
