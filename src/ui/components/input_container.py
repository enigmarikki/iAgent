from textual import events
from textual.widgets import Input, Label, Header, Footer, Static, Markdown
from textual.app import App, ComposeResult


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
