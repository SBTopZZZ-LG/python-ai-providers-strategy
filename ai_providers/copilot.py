"""Copilot AI provider implementation."""


from dataclasses import dataclass
from typing import Optional
from copilot import CopilotClient, CopilotSession

from .base import BaseAIProvider, BaseAIProviderOptions


@dataclass
class CopilotProviderOptions(BaseAIProviderOptions):
    """Options for initializing the Copilot provider."""

    client: CopilotClient
    model: str
    timeout: float


class CopilotProvider(BaseAIProvider[CopilotProviderOptions]):
    """
    Copilot AI provider implementation.
    """

    session: Optional[CopilotSession]

    def __init__(self, options: CopilotProviderOptions):
        super().__init__(options)
        self.session = None

    async def initialize_session(self):
        """
        Initialize the Copilot session.
        """
        options = self.options

        if options.client is None:
            raise ValueError("Copilot client must be provided for session initialization.")
        if options.client.get_state() != 'connected':
            raise ValueError("Copilot client must be connected to initialize session.")
        if options.model is None or str.strip(options.model) == "":
            raise ValueError("Valid model name must be provided for session initialization.")
        if options.timeout <= 0:
            raise ValueError("Timeout must be a positive floating point number for session initialization.")

        if self.session is not None:
            print("Warning: Copilot session already initialized. Reinitializing session.")
            await self.dispose_session()

        self.session = await options.client.create_session({"model": options.model})

    async def send_message_and_await_response(self, message: str) -> str:
        """
        Send a message to the Copilot AI provider and await a response.
        """

        if self.session is None:
            raise ValueError("Copilot session is not initialized.")

        response = await self.session.send_and_wait(
            {"prompt": message},
            timeout=self.options.timeout
        )

        if response is None:
            raise RuntimeError("Received null response from Copilot session.")
        if response.data is None:
            raise RuntimeError("Received response with null data from Copilot session.")

        return response.data.content or ""

    async def dispose_session(self):
        """
        Dispose of the Copilot session.
        """

        if self.session is None:
            return

        try:
            await self.session.destroy()
        except Exception as e:
            raise RuntimeError(f"Failed to dispose Copilot session: {str(e)}") from e
        finally:
            self.session = None
