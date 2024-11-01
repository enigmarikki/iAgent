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
from src.services.system_status import SystemStatus
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
        self.tickers: Dict[str, None | str] = {"BTC": None, "ETH": None, "INJ": None}
        self.last_prices:Dict[str,  float] = {}

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
            now, 
            self._format_price(self.tickers["BTC"]),
            self._format_price(self.tickers["ETH"]),
            self._format_price(self.tickers["INJ"])
        )
        if new_content != self._content_cache:
            self._content_cache = new_content
            self.static_content.update(new_content)

        # Format the content with real-time data

    def _generate_content(self, now: datetime, btc: None|str=None, eth: None|str=None, inj: None|str=None) -> str:
        """Generate beautifully formatted panel content."""
        return f"""\n
                [yellow] System Status[/]
                    • [dim]Time (UTC):[/] {now.strftime('%Y-%m-%d %H:%M:%S')}
                    • [dim]Session:[/] {time.strftime('%H:%M:%S', time.gmtime())}
                    • [dim]Connection:[/] [green]●[/] Active

                [yellow] Market Overview[/]
                    • [dim]BTC/USD:[/] {btc if btc else '[dim]Fetching...[/]'}
                    • [dim]ETH/USD:[/] {eth if eth else '[dim]Fetching...[/]'}
                    • [dim]INJ/USD:[/] {inj if inj else '[dim]Fetching...[/]'}

                [yellow] Commands & Shortcuts[/]
                    • [dim]CTRL+B[/] Toggle panel
                    • [dim]CTRL+Q[/] Quit app
                    • [dim]exit[/] End session
"""

    def _format_price(self, price: None|str) -> str:
        """Format price with color based on value change."""
        if not price:
            return '[dim]Fetching...[/]'
    
        # Add color based on price change (you can modify this logic)
        try:
            value = float(price)
            last_value = self.last_prices.get(price, value)
            self.last_prices[price] = value
        
            if value > last_value:
                return f'[green]${value:,.2f} ↑[/]'
            elif value < last_value:
                return f'[red]${value:,.2f} ↓[/]'
            else:
                return f'[white]${value:,.2f}[/]'
        except (ValueError, TypeError):
            return f'[white]${price}[/]'

    async def _update_loop(self) -> None:
        """Periodic update loop for real-time information."""
        update_interval = CONFIG.get("UPDATE_INTERVAL", 1)
        while True:
            current_time = time.time()
            if current_time - self._last_update >= update_interval:

                self._last_update = current_time
                now = datetime.now(pytz.UTC)
                
                # Update prices
                async with CoinbaseClient() as client:
                    prices = await client.get_multiple_prices(["BTC", "ETH", "INJ"])
                    self.tickers.update(prices)

                # Update display with formatted content
                new_content = self._generate_content(
                    now,
                    self._format_price(self.tickers["BTC"]),
                    self._format_price(self.tickers["ETH"]),
                    self._format_price(self.tickers["INJ"])
                )
                
                if new_content != self._content_cache:
                    self._content_cache = new_content
                    self.static_content.update(new_content)
                    
            await asyncio.sleep(update_interval)

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
