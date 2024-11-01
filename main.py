import os
import openai
from src.app.chat_app import ChatApp
import typer


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
