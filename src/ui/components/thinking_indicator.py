from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio
from typing import Optional
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Header, Footer, Static, Markdown
from src.app.config import CONFIG, THINKING_PATTERNS


class ThinkingIndicator(Static):
    """A thinking indicator widget with simple animation."""

    DEFAULT_CSS = """
    ThinkingIndicator {
        layout: horizontal;
        height: auto;
        margin: 0 8 0 0;
        padding: 0;
        opacity: 0;
        transition: opacity 300ms linear, offset 300ms linear;
    }
    ThinkingIndicator.--show {
        opacity: 1;
        offset: 0 0;
    }
    .thinking-content {
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    .dots {
        color: $text-muted;
        margin-left: 4;
    }
    """

    def __init__(self):
        super().__init__()
        self.dots_label: Label = Label(
            THINKING_PATTERNS[0], classes="dots", id="thinking-dots"
        )
        self.animation_task: Optional[asyncio.Task] = None
        self._is_animating: bool = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Static(classes="thinking-content"):
            yield self.dots_label

    async def animate_dots(self) -> None:
        """Animate the dots with a simple pattern."""
        if self._is_animating:
            return
        self._is_animating = True
        index = 1
        while True and self._is_animating:
            self.dots_label.update(THINKING_PATTERNS[index])
            index = (index + 1) % len(THINKING_PATTERNS)
            await asyncio.sleep(CONFIG.get("ANIMATION_INTERVAL", 0.1))

    async def show_indicator(self) -> None:
        """Show the indicator and start animation."""
        await asyncio.sleep(CONFIG.get("ANIMATION_INTERVAL", 0.1))
        self.add_class("--show")
        self.animation_task = asyncio.create_task(self.animate_dots())

    async def stop_animation(self, attribute=None, complete=None) -> None:
        """Stop the animation task."""
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
