from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from textual.containers import ScrollableContainer
from collections import deque

# if TYPE_CHECKING:
from src.ui.components.thinking_indicator import ThinkingIndicator
from src.ui.components.message import Message
from src.app.config import CONFIG


class ChatContainer(ScrollableContainer):
    """Container for chat messages."""

    DEFAULT_CSS = """
    ChatContainer {
        background: $surface-darken-1;
        padding: 1;
        height: 1fr;
        width: 100%;
        overflow-y: scroll;
        transition: background 300ms linear;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_queue = deque(maxlen=100)
        self.processing = False
        self.thinking_indicator = None

    async def add_message(self, role: str, content: str) -> None:
        """Add a message to the queue and process it."""
        self.message_queue.append((role, content))
        if not self.processing:
            await self.process_message_queue()

    async def show_thinking(self) -> None:
        """Show the thinking indicator."""
        self.thinking_indicator = ThinkingIndicator()
        await self.mount(self.thinking_indicator)
        await self.thinking_indicator.show_indicator()
        self.scroll_end()

    async def hide_thinking(self) -> None:
        """Hide and remove the thinking indicator."""
        if self.thinking_indicator:
            await self.thinking_indicator.stop_animation()
            if self.thinking_indicator.parent:
                await self.thinking_indicator.remove()
            self.thinking_indicator = None

    async def process_message_queue(self) -> None:
        """Process messages in the queue one by one."""
        self.processing = True
        while self.message_queue:
            role, content = self.message_queue.popleft()
            message = Message(role, content)
            await self.mount(message)
            await message.show_message()
            self.scroll_end()
            await asyncio.sleep(CONFIG.get("UPDATE_INTERVAL", 0.1))
        self.processing = False
