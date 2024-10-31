import os
from datetime import datetime, timedelta
import pytz
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Header, Footer, Static, Markdown
from textual.containers import ScrollableContainer, Container
from textual.reactive import reactive
from textual.binding import Binding
from textual import events
import time
from swarm import Swarm, Agent
import openai
from typing import List, Dict
import typer
from collections import deque

import aiohttp
import asyncio
from typing import Optional, Dict, Any
import json



UPDATE_INTERVAL = 0.2
ANIMATION_INTERVAL = 0.1
MESSAGE_TRANSITION_DELAY = 0.1
QUIT_DELAY = 0.1
THINKING_PATTERNS = ["💭   ", "💭.  ", "💭.. ", "💭..."]
ROLE_PREFIXES = {
    "assistant": "💡 Jarvis",
    "system": "⚙️  System",
    "user": "👤 You"
}



class CoinbaseClient:
    def __init__(self, max_retries: int = 3, retry_delay: float = 0.5, rate_limit: int = 30):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.coinbase.com/v2"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit = rate_limit
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": "CoinbaseClient/1.0"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        async with self._lock:
            now = time.time()
            # Remove old requests from tracking
            self._request_times = [t for t in self._request_times if now - t < 1.0]
            
            if len(self._request_times) >= self.rate_limit:
                sleep_time = 1.0 - (now - self._request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            self._request_times.append(now)

    async def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None) -> Dict:
        """Make an API request with retries and error handling"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")

        await self._enforce_rate_limit()

        for attempt in range(self.max_retries):
            try:
                async with self.session.request(method, f"{self.base_url}/{endpoint}", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit exceeded
                        retry_after = float(response.headers.get('Retry-After', self.retry_delay))
                        await asyncio.sleep(retry_after)
                    elif response.status >= 500:  # Server error
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        error_data = await response.json()
                        raise aiohttp.ClientError(f"API Error: {error_data.get('message', 'Unknown error')}")
                        
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue
            except Exception as e:
                raise

        raise aiohttp.ClientError(f"Failed after {self.max_retries} attempts")

    async def get_price(self, ticker: str) -> Optional[float]:
        """Get current token price in USD"""
        try:
            data = await self._make_request(f"prices/{ticker}-USD/spot")
            return float(data['data']['amount'])
        except (KeyError, ValueError) as e:
            return None
        except Exception as e:
            return None

    async def get_multiple_prices(self, tickers: List[str]) -> Dict[str, Optional[float]]:
        """Get prices for multiple tokens concurrently"""
        async def get_single_price(ticker: str) -> tuple[str, Optional[float]]:
            price = await self.get_price(ticker)
            return ticker, price

        tasks = [get_single_price(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            ticker: price for ticker, price in results 
            if not isinstance(price, Exception)
        }

    async def get_price_history(self, ticker: str, days: int = 7) -> Optional[List[Dict]]:
        """Get historical price data"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "granularity": "86400"  # Daily candles
        }
        
        try:
            data = await self._make_request(f"prices/{ticker}-USD/historic", params=params)
            return data['data']
        except Exception as e:
            return None


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
        self.tickers = {"BTC":None, "ETH":None, "INJ":None}

    def compose(self) -> ComposeResult:
        yield self.static_content
        #self.update_content()
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

    async def async_update_content(self) -> None:
        """Update panel content with caching."""
        current_time = time.time()
        if current_time - self._last_update < UPDATE_INTERVAL:
            return

        self._last_update = current_time
        now = datetime.now(pytz.UTC)
        async with CoinbaseClient() as client:
            prices = await client.get_multiple_prices(["BTC", "ETH", "INJ"])
            # Update tickers with new prices
            self.tickers.update(prices)

        new_content = self._generate_content(now, self.tickers["BTC"], self.tickers["ETH"], self.tickers["INJ"])
        if new_content != self._content_cache:
            self._content_cache = new_content
            self.static_content.update(new_content)           

        # Format the content with real-time data
    def _generate_content(self, now: datetime, btc:None|str=None, eth:None|str=None, inj:None|str=None) -> str:
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
        while True:
            await self.async_update_content()
            await asyncio.sleep(UPDATE_INTERVAL)  # Update every second

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
        self.dots_label: Optional[Label] = None
        self.animation_task: Optional[asyncio.Task] = None
        self._is_animating: bool = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Static(classes="thinking-content"):
            self.dots_label = Label(THINKING_PATTERNS[0], classes="dots", id="thinking-dots")
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
            await asyncio.sleep(ANIMATION_INTERVAL)

    async def show_indicator(self) -> None:
        """Show the indicator and start animation."""
        await asyncio.sleep(ANIMATION_INTERVAL)
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
        await asyncio.sleep(ANIMATION_INTERVAL)
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
                "user": f"{time.strftime('%H:%M', time.localtime())}"
            }
            yield Label(f'{ROLE_PREFIXES[self.role]} • {time.strftime("%H:%M", time.localtime())}', classes=f"{self.role}-header-content")
        with Static(classes=f"message-content {self.role}-content"):
            yield Markdown(self.content)
            #yield Label(self.content)



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
        self.message_queue = deque()
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
            await asyncio.sleep(UPDATE_INTERVAL)
        self.processing = False


class InputContainer(Static):
    """Container for the chat input field."""

    CSS = """
    InputContainer {
        background: $surface-darken-1;
        padding: 0;
        layout: horizontal;
        width: 100%;
        dock: bottom;
        border: none;
    }

    Input {
        dock: bottom;
        width: 100%;
        height: 1;
        margin: 0;
        border: none;
        background: $surface-darken-1;
        color: $text-muted;  /* Dimmed text color by default */
        padding: 0 1;
        opacity: 0.7;  /* Slightly dimmed by default */
        transition: color 200ms ease, opacity 200ms ease, background 200ms ease;
    }

    Input:focus {
        border: none;
        background: $surface-darken-2;
        color: $text;  /* Full brightness text when focused */
        opacity: 1;  /* Full opacity when focused */
    }

    Input.-valid {
        border: none;
    }

    Input.-valid:focus {
        border: none;
    }

    /* Style for the placeholder text */
    Input::placeholder {
        color: $text-muted;
        opacity: 0.5;
        border: none;
    }

    Input:focus::placeholder {
        opacity: 0.7;
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(
            id="message-input",
            placeholder="Type your message... (ESC to clear)",
        )

    def clear_input(self) -> None:
        """Clear input and maintain focus."""
        input_widget = self.query_one("#message-input", Input)
        input_widget.value = ""
        input_widget.focus()

    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.clear_input()


class ChatApp(App):
    """A Textual chat application."""

    # ... [Previous CSS and BINDINGS remain unchanged]

    BINDINGS = [
        Binding("ctrl+b", "toggle_right_panel", "Toggle Right Panel"),
        Binding("ctrl+q", "quit", "Quit Application")
    ]

    CSS = """
    Panel {
        width: 30%;
        height: 100%;
    }

    Panel.right {
        dock: right;
        background: $panel;
        border-left: solid $primary;
    }

    Panel.collapsed {
        display: none;
    }

    .panel-content {
        padding: 1 2;
        height: 100%;
    }

    #main-container {
        width: 100%;
        height: 100%;
        layout: vertical;
    }

    .main-content {
        padding: 1 2;
        height: 100%;
        border: solid $accent;
    }

    .shortcut-info {
        text-align: center;
        padding: 1;
    }
    """


    def __init__(self):
        super().__init__()
        self.agent = Agent(name="AI Agent", instructions="You are a helpful agent.")
        self.client = Swarm()
        self.messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "You are a helpful InjectiveLab AI assistant.",
            }
        ]
        self._initialize_messages()

    def _initialize_messages(self) -> None:
        """Initialize system messages."""
        self.messages.append({
            "role": "system",
            "content": "You are a helpful InjectiveLab AI assistant."
        })

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        right_panel_content = (
            "[bold]InjectiveLab AI Assistant[/bold]\n\n"
            "[yellow]Commands & Shortcuts:[/yellow]\n"
            "• [bold]CTRL+B[/bold] - Toggle this panel\n"
            "• [bold]CTRL+Q[/bold] - Quit application\n"
            "• Type 'exit' - End conversation\n\n"
            "[yellow]Available Functions:[/yellow]\n"
            "• Chat with AI assistant\n"
            "• Get market analysis\n"
            "• Query blockchain data\n"
            "• Execute trading strategies\n\n"
            "[yellow]Tips:[/yellow]\n"
            "• Be specific in your questions\n"
            "• Use clear, concise language\n"
            "• Review previous messages for context\n\n"
            "[yellow]Resources:[/yellow]\n"
            "• Injective Docs\n"
            "• Trading Documentation\n"
            "• API Reference\n"
            "• Community Forum\n\n"
            "[yellow]Support:[/yellow]\n"
            "• Discord: InjectiveLabs\n"
            "• Email: support@injective.com\n"
            "• GitHub: injectivelabs/sdk-ts"
        )

        yield Container(
            Panel(right_panel_content, "right"),
            ChatContainer(id="chat"),
            InputContainer(id="user-input"),
            id="main-container"
        )
        yield Footer()

    def action_toggle_right_panel(self) -> None:
        """Toggle right panel action."""
        self.query_one("Panel.right").toggle()


    async def on_mount(self) -> None:
        """Handle app mount event."""
        input_widget = self.query_one("#message-input")
        #input_widget.placeholder = "Type your message..."
        input_widget.focus()

        await self.query_one(ChatContainer).add_message(
            "system",
            "Welcome to the InjectiveLab AI Agent CLI!",
        )

    async def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key == "enter":
            input_widget = self.query_one("#message-input")
            user_input = input_widget.value
            self.query_one(InputContainer).clear_input()
            await self.handle_input(user_input)


    async def handle_input(self, user_input: str) -> None:
        """Process user input."""
        if not user_input.strip():
            return

        chat_container = self.query_one(ChatContainer)

        try:
            if user_input.lower() in ["exit", "quit"]:
                await self.action_quit()
                return

            await self._process_message(chat_container, user_input)

        except Exception as e:
            await self._handle_error(chat_container, e)


    async def _process_message(self, chat_container: ChatContainer, user_input: str) -> None:
        """Process a single message with proper error handling."""
        await chat_container.add_message("user", user_input)
        self.messages.append({"role": "user", "content": user_input})

        await chat_container.show_thinking()

        try:
            async with asyncio.timeout(30):  # Add timeout for API calls
                response = await asyncio.to_thread(
                    self.client.run,
                    agent=self.agent,
                    messages=self.messages
                )

                await chat_container.hide_thinking()

                if response.messages:
                    for message in response.messages:
                        await chat_container.add_message(
                            message["role"],
                            message["content"]
                        )
                        self.messages.append(message)

        except asyncio.TimeoutError:
            await self._handle_error(chat_container, "Request timed out. Please try again.")
        except Exception as e:
            await self._handle_error(chat_container, e)

    async def action_quit(self) -> None:
        """Quit the application."""
        await self.query_one(ChatContainer).add_message("system", "Goodbye! 👋")
        await asyncio.sleep(QUIT_DELAY)
        self.exit()


def main(api_key: None | str = None):
    """Run the chat application."""
    if api_key:
        openai.api_key = api_key
    elif os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
    else:
        print("Error: OpenAI API key not provided")
        return

    app = ChatApp()
    app.run()


if __name__ == "__main__":
    typer.run(main)
