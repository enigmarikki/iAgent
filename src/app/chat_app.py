from __future__ import annotations
import asyncio
import aiohttp
import openai
from textual import events
from swarm import Swarm, Agent
from typing import Dict, List
from textual import events
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Container
from textual.widgets import Input, Label, Header, Footer, Static, Markdown
from src.app.config import CONFIG
from src.ui.components.chat_container import ChatContainer
from src.ui.components.input_container import InputContainer
from src.ui.components.panel import Panel
from src.agent.agents import triage_agent, sales_agent, refunds_agent


class ChatApp(App):
    """A Textual chat application."""

    # ... [Previous CSS and BINDINGS remain unchanged]

    BINDINGS = [
        Binding("ctrl+b", "toggle_right_panel", "Toggle Right Panel"),
        Binding("ctrl+q", "quit", "Quit Application"),
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
        self.agent =triage_agent #Agent(name="AI Agent", instructions="You are a helpful agent.")
        self.agents = [triage_agent,sales_agent, refunds_agent]
        self.client = Swarm()
        self.messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "You are a helpful InjectiveLab AI assistant.",
            }
        ]
        self._initialize_messages()
        self.MAX_MESSAGES = 1000

        self.ERROR_MESSAGES = {
            openai.APIError: "OpenAI API error occurred. Please try again later.",
            openai.RateLimitError: "Rate limit exceeded. Please wait a moment before trying again.",
            openai.APIConnectionError: "Connection to OpenAI failed. Please check your internet connection.",
            openai.BadRequestError: "Invalid request to OpenAI API. Please try again.",
            asyncio.TimeoutError: "Request timed out. Please try again.",
            aiohttp.ClientError: "Network error occurred. Please check your connection.",
            Exception: "An unexpected error occurred. Please try again.",
        }

    async def _handle_error(
        self, chat_container: ChatContainer, error: Exception
    ) -> None:
        """Handle different types of errors and display appropriate messages."""
        error_type = type(error)
        error_message = self.ERROR_MESSAGES.get(error_type, str(error))

        # Log the error for debugging
        # logging.error(f"Error occurred: {error_type.__name__} - {str(error)}")

        # Hide thinking indicator if it's showing
        await chat_container.hide_thinking()

        # Show error message to user
        await chat_container.add_message("system", f"⚠️ {error_message}")

    async def handle_api_error(
        self, chat_container: ChatContainer, error: Exception
    ) -> bool:
        """Specifically handle API-related errors."""
        if isinstance(error, openai.RateLimitError):
            await asyncio.sleep(1)  # Basic retry delay
            return True  # Indicate retry is possible

        await self._handle_error(chat_container, error)
        return False  # Indicate no retry

    def _initialize_messages(self) -> None:
        """Initialize system messages."""
        self.messages.append(
            {
                "role": "system",
                "content": "You are a helpful InjectiveLab AI assistant.",
            }
        )

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            Panel("right"),
            ChatContainer(id="chat"),
            InputContainer(id="user-input"),
            id="main-container",
        )
        yield Footer()

    def action_toggle_right_panel(self) -> None:
        """Toggle right panel action."""
        self.query_one("Panel.right").toggle()

    async def on_mount(self) -> None:
        """Handle app mount event."""
        input_widget = self.query_one("#message-input")
        # input_widget.placeholder = "Type your message..."
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
            self.cleanup_old_messages()

        except Exception as e:
            await self._handle_error(chat_container, e)

    async def _process_message(
        self, chat_container: ChatContainer, user_input: str
    ) -> None:
        """Process a single message with proper error handling."""
        await chat_container.add_message("user", user_input)
        self.messages.append({"role": "user", "content": user_input})

        await chat_container.show_thinking()

        try:
            async with asyncio.timeout(30):  # Add timeout for API calls
                response = await asyncio.to_thread(
                    self.client.run, agent=self.agent, messages=self.messages
                )

                await chat_container.hide_thinking()

                if response.messages:
                    for message in response.messages:
                        await chat_container.add_message(
                            message["role"], message["content"]
                        )
                        self.messages.append(message)

        except asyncio.TimeoutError:
            await self._handle_error(
                chat_container, Exception("Request timed out. Please try again.")
            )
        except Exception as e:
            await self._handle_error(chat_container, e)

    def cleanup_old_messages(self):
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES :]

    async def action_quit(self) -> None:
        """Quit the application."""
        await self.query_one(ChatContainer).add_message("system", "Goodbye! 👋")
        await asyncio.sleep(CONFIG.get("QUIT_DELAY", 0.1))
        self.exit()
