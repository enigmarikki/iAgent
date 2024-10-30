import os
import asyncio
from textual.app import App, ComposeResult
from textual.validation import Function
from textual.widgets import Input, Label, Pretty,  Static
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual import events
from textual.scroll_view import ScrollView
from textual.containers import Horizontal, Vertical
from textual.message import Message as TextualMessage
from textual import on
import time
from swarm import Swarm, Agent
import openai
from typing import List, Dict
import typer
from collections import deque

class ThinkingIndicator(Static):
    """A thinking indicator widget with simple animation."""
    DEFAULT_CSS = """
    ThinkingIndicator {
        layout: horizontal;
        height: auto;
        margin: 0 1 0 0;
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
        margin-left: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.dots_label = None
        self.animation_task = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Static(classes="thinking-content"):
            yield Label("💭 Thinking")
            self.dots_label = Label("...", classes="dots", id="thinking-dots")
            yield self.dots_label

    async def animate_dots(self) -> None:
        """Animate the dots with a simple pattern."""
        patterns = ["   ", ".  ", ".. ", "..."]
        index = 0
        while True:
            self.dots_label.update(patterns[index])
            index = (index + 1) % len(patterns)
            await asyncio.sleep(0.3)

    async def show_indicator(self) -> None:
        """Show the indicator and start animation."""
        await asyncio.sleep(0.1)
        self.add_class("--show")
        self.animation_task = asyncio.create_task(self.animate_dots())

    async def stop_animation(self) -> None:
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
          padding: 0;
          opacity: 0;
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
          margin: 0;
      }

      .message-content {
          padding: 0 1;
      }

      .user-message .message-content {
          background: #3b82f6;
          color: $text;
      }

      .assistant-message .message-content {
          background: $surface;
          color: $text;
      }

      .system-message .message-content {
          background: $warning;
          color: $text;
      }

      Message > .header {
          layout: horizontal;
          height: auto;
          padding: 0 0 0 0;
      }

      .user-message > .header {
          align-horizontal: right;
      }

      Message .assistant {
          color: #4ade80;
          text-style: bold;
      }

      Message .system {
          color: #fbbf24;
          text-style: bold;
      }

      Message .user {
          color: #60a5fa;
          text-style: bold;
      }

      Message .time {
          color: $text-muted;
      }

      Message .separator {
          color: $text-muted;
          margin: 0 1;
      }
      """


    def __init__(self, role: str, content: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.role = role
        self.content = content

    async def show_message(self) -> None:
        """Animate the message appearance."""
        await asyncio.sleep(0.1)
        self.add_class("--show")

    def on_mount(self) -> None:
        """Handle message mount event."""
        self.add_class(f"{self.role}-message")

    def compose(self) -> ComposeResult:
        """Compose the message content."""
        ROLE_PREFIXES = {
            "assistant": "💡 Assistant",
            "system": "⚙️  System",
            "user": "👤 You"
        }
        with Static(classes="header"):
            yield Label(f'{ROLE_PREFIXES[self.role]} • {time.strftime("%H:%M", time.localtime())}', classes=self.role)
        with Static(classes=f"message-content {self.role}-content"):
            yield Label(self.content)




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
            await asyncio.sleep(0.3)
        self.processing = False


class InputContainer(Static):
    """Container for the chat input field."""

    CSS = """
    InputContainer {
        background: $surface-darken-1;
        padding: 1;
    }

    Input {
        margin: 0;
        border: none;
        background: transparent;
        color: $text;
    }

    Input.-valid {
        border: none;
    }

    Input.-valid:focus {
        border: none;
    }

    Input:focus {
        border: none;
        background: transparent;
    }

    Label {
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        # yield Label("Enter an even number between 1 and 100 that is also a palindrome.")
        yield Input(
            id="message-input",
            placeholder="Enter a number...",
        )


class ChatApp(App):
    """A Textual chat application."""

    # ... [Previous CSS and BINDINGS remain unchanged]

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

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield ChatContainer(id="chat")
        yield InputContainer(id="user-input")

    async def on_mount(self) -> None:
        """Handle app mount event."""
        input_widget = self.query_one("#message-input")
        input_widget.placeholder = "Type your message..."
        input_widget.focus()

        await self.query_one(ChatContainer).add_message(
            "system",
            "Welcome to the InjectiveLab AI Agent CLI!\nType 'exit' or press Ctrl+C to end the conversation.",
        )

    async def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key == "enter":
            input_widget = self.query_one("#message-input")
            await self.handle_input(input_widget.value)
            input_widget.value = ""

    async def handle_input(self, user_input: str) -> None:
        """Process user input."""
        if not user_input.strip():
            return

        chat_container = self.query_one(ChatContainer)

        if user_input.lower() in ["exit", "quit"]:
            await self.action_quit()
            return

        # Add user message
        await chat_container.add_message("user", user_input)
        self.messages.append({"role": "user", "content": user_input})

        # Show thinking indicator
        await chat_container.show_thinking()

        # Get AI response
        try:
            response = self.client.run(agent=self.agent, messages=self.messages)

            # Hide thinking indicator
            await chat_container.hide_thinking()

            if response.messages:
                for message in response.messages:
                    await chat_container.add_message(
                        message["role"], message["content"]
                    )
                    self.messages.append(
                        {"role": "assistant", "content": message["content"]}
                    )
        except Exception as e:
            # Hide thinking indicator in case of error
            await chat_container.hide_thinking()
            await chat_container.add_message("system", f"Error: {str(e)}")

    async def action_quit(self) -> None:
        """Quit the application."""
        await self.query_one(ChatContainer).add_message("system", "Goodbye! 👋")
        await asyncio.sleep(1)
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
