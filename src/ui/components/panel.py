from __future__ import annotations
import asyncio
import time
import pytz
from datetime import datetime
from typing import Optional, Dict
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Input, Label, Header, Footer, Static, Markdown
from src.services.coinbase_client import CoinbaseClient
from src.app.config import CONFIG, ROLE_PREFIXES


class Panel(Container):
    """A collapsible panel with real-time updates."""

    def __init__(self, content: str, position: str = "right") -> None:
        super().__init__()
        self.content = content
        self.position = position
        self.is_expanded = reactive(True)
        self.add_class(position)
        self._update_task: Optional[asyncio.Task] = None
        self.static_content = Static("", id="panel-content")
        self._last_update: float = 0
        self._content_cache: str = ""
        self.tickers: Dict[str, None | float] = {"BTC": None, "ETH": None, "INJ": None}

    def compose(self) -> ComposeResult:
        yield self.static_content
        self.start_updates()

    def toggle(self) -> None:
        """Toggle the panel expansion state."""
        self.is_expanded = not self.is_expanded
        self.toggle_class("collapsed")

        # Start or stop updates based on panel state
        if self.is_expanded:
            self.start_updates()
        else:
            self.stop_updates()

    async def update_content(self, update_interval: float = 1) -> None:
        """Update panel content with caching."""
        current_time = time.time()
        if current_time - self._last_update < update_interval:
            return

        self._last_update = current_time
        now = datetime.now(pytz.UTC)
        async with CoinbaseClient() as client:
            prices = await client.get_multiple_prices(["BTC", "ETH", "INJ"])
            # Update tickers with new prices
            self.tickers.update(prices)

        new_content = self._generate_content(
            now, self.tickers["BTC"], self.tickers["ETH"], self.tickers["INJ"]
        )
        if new_content != self._content_cache:
            self._content_cache = new_content
            self.static_content.update(new_content)

        # Format the content with real-time data

    def _generate_content(
        self,
        now: datetime,
        btc: None | float = None,
        eth: None | float = None,
        inj: None | float = None,
    ) -> str:
        """Generate panel content with current data."""
        return f"""[bold]InjectiveLab AI Assistant[/bold]\n\n
                  [yellow]System Status:[/yellow]\n
                  • Time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}\n
                  • Active Session: {time.strftime('%H:%M:%S', time.gmtime())}\n
                  • Connection: Active\n\n
                  [yellow]Market Overview:[/yellow]\n
                  • BTC/USD: {btc if btc else "Fetching..."}\n
                  • ETH/USD: {eth if eth else "Fetching..."}\n
                  • INJ/USD: {inj if inj else "Fetching..."}\n\n
                  [yellow]Commands & Shortcuts:[/yellow]\n
                  • [bold]CTRL+B[/bold] - Toggle this panel\n
                  • [bold]CTRL+Q[/bold] - Quit application\n
                  • Type 'exit' - End conversation"""

    async def _update_loop(self) -> None:
        """Periodic update loop for real-time information."""
        update_interval = CONFIG.get("UPDATE_INTERVAL", 1)
        while True:
            await self.update_content(update_interval)
            await asyncio.sleep(update_interval)  # Update every second

    def start_updates(self) -> None:
        """Start the update loop."""
        if self._update_task is None:
            self._update_task = asyncio.create_task(self._update_loop())

    def stop_updates(self) -> None:
        """Stop the update loop."""
        if self._update_task is not None:
            self._update_task.cancel()
            self._update_task = None

    async def on_unmount(self) -> None:
        """Clean up when the panel is unmounted."""
        self.stop_updates()
