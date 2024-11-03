from __future__ import annotations
import time
import asyncio
from typing import TYPE_CHECKING
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Header, Footer, Static, Markdown

# if TYPE_CHECKING:
from src.app.config import CONFIG, ROLE_PREFIXES


class Message(Static):
    """A message in the chat."""

    DEFAULT_CSS = """
    Message {
        layout: vertical;
        height: auto;
        margin: 0;
        padding: 0 0;
        opacity: 0;
        offset-y: 0;
        transition: opacity 300ms linear, offset 300ms linear;
        width: 100%;
    }

    Message.--show {
        opacity: 1;
        offset: 0 0;
    }

    Message.user-message {
        align-horizontal: right;
        margin: 0 1 0 8;
    }

    Message.assistant-message {
        align-horizontal: left;
        margin: 0 8 0 1;
    }

    Message.system-message {
        align-horizontal: center;
    }

    .message-content {
        padding: 1 2;
        width: auto;  /* Limit maximum width of messages */
    }

    .user-message .message-content {
        background: #3b82f6;
        color: $text;
        width: auto;
        align-horizontal: right;
        margin-left: 8;  /* Push to right */
    }

    .assistant-message .message-content {
        background: $surface;
        color: $text;
        width: auto;
        align-horizontal: left;
        margin-right: 8;  /* Push to left */
    }

    .system-message .message-content {
        background: $warning;
        color: $text;
        width: auto;
        width: 80%;  /* System messages can be wider */
    }

    Message > .header {
        layout: horizontal;
        height: auto;
        padding: 0 1 0 1;
        width: 100%;
    }

    .user-message > .header {
        color: #60a5fa;
        align-horizontal: right;
        padding-right: 1;
        text-style: bold;
    }

    .user-header-content {
        color: #60a5fa;
        align-horizontal: right;
        text-style: bold;
    }

    .system-header-content {
        color: #fbbf24;
        text-style: bold;
    }

    .assistant-header-content {
        color: #34d399;
        align-horizontal: right;
        text-style: bold;
    }

    .header-container {
        width: 100%;
    }

    .user-message .header-container {
        align-horizontal: right;
        padding-right: 1;
    }

    /* Label within message content */
    .message-content Label {
        text-align: left;
        width: 100%;
    }
    """

    def __init__(self, role: str, content: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.role = role
        self.content = content

    async def show_message(self) -> None:
        """Animate the message appearance."""
        # await asyncio.sleep(ANIMATION_INTERVAL)
        await asyncio.sleep(CONFIG.get("ANIMATION_INTERVAL", 0.1))
        self.add_class("--show")

    def on_mount(self) -> None:
        """Handle message mount event."""
        self.add_class(f"{self.role}-message")

    def compose(self) -> ComposeResult:
        """Compose the message content."""

        with Static(classes="header"):
            headers = {
                "assistant": f"{time.strftime('%H:%M', time.localtime())}",
                "system": f"{time.strftime('%H:%M', time.localtime())}",
                "user": f"{time.strftime('%H:%M', time.localtime())}",
            }
            yield Label(
                f'{ROLE_PREFIXES.get(self.role, self.role)} • {time.strftime("%H:%M", time.localtime())}',
                classes=f"{self.role}-header-content",
            )
        with Static(classes=f"message-content {self.role}-content"):
            yield Markdown(self.content)
