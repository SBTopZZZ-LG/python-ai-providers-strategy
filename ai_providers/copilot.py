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


class CopilotProvider(BaseAIProvider[CopilotProviderOptions]):
    """
    Copilot AI provider implementation.
    """

    RESPONSE_TIMEOUT_IN_SECONDS = 7200

    session: Optional[CopilotSession]

    def __init__(self, options: CopilotProviderOptions):
        super().__init__(options)
        self.session = None

    async def initialize_session(self):
        """
        Initialize the Copilot session.
        """
        options = self.options

        assert options.client is not None, \
            "Copilot client must be provided for session initialization."
        assert options.client.get_state() == 'connected', \
            "Copilot client must be connected to initialize session."
        assert options.model is not None and str.strip(options.model) != "", \
            "Model name must be provided for session initialization."

        if self.session is not None:
            print("Warning: Copilot session already initialized. Reinitializing session.")
            await self.dispose_session()

        self.session = await options.client.create_session({"model": options.model})

    async def send_message_and_await_response(self, message: str) -> str:
        """
        Send a message to the Copilot AI provider and await a response.
        """

        assert self.session is not None, \
            "Copilot session must be initialized before sending messages."

        response = await self.session.send_and_wait(
            {"prompt": message},
            timeout=self.RESPONSE_TIMEOUT_IN_SECONDS
        )

        assert response is not None, "Received null response from Copilot session."
        assert response.data is not None, "Received response with null data from Copilot session."

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
            print(f"Error disposing Copilot session: {e}")
        finally:
            self.session = None
