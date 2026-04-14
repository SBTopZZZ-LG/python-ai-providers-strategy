"""Base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass
class BaseAIProviderOptions:
    """Base options for all AI providers."""


T = TypeVar('T', bound=BaseAIProviderOptions)


class BaseAIProvider(ABC, Generic[T]):
    """Abstract base class for AI providers.

    Args:
        options: Provider-specific options used to configure the provider.
    """

    options: T

    def __init__(self, options: T):
        """Initialize the base provider.

        Args:
            options: Provider-specific options object.
        """

        self.options = options

    @abstractmethod
    async def initialize_session(self):
        """Initialize the AI provider session.

        Returns:
            None

        Raises:
            Exception: Implementation-specific initialization failures.
        """

    @abstractmethod
    async def send_message_and_await_response(self, message: str) -> str:
        """Send a message to the AI provider and await a response.

        Args:
            message: Prompt content to send to the provider.

        Returns:
            Provider response text.

        Raises:
            Exception: Implementation-specific request/response failures.
        """

    @abstractmethod
    async def dispose_session(self):
        """Dispose of the AI provider session.

        Returns:
            None

        Raises:
            Exception: Implementation-specific disposal failures.
        """
