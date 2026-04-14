"""Factory for creating AI provider instances based on a generic configuration."""

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


async def create_ai_provider(config: AIProviderConfig) -> BaseAIProvider:
    """
    Factory method to create an AI provider instance mapped from a generic config object.
    The caller doesn't need to know the specific options dataclass required by the provider.
    """

    if config.provider_type == ProviderType.COPILOT:
        import copilot

        client = copilot.CopilotClient()
        try:
            await client.start()
        except Exception as e:
            raise RuntimeError(f"Failed to start Copilot client: {str(e)}") from e

        options = CopilotProviderOptions(
            client=client,
            model=config.model
        )
        return CopilotProvider(options)

    raise ValueError(f"Unknown provider type: {config.provider_type}")
