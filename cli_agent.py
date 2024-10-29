import platform
import sys
import asyncio
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
import openai
import os
from typing import Optional
from swarm import Swarm, Agent
import time

from typing import Callable
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import prompt
import prompt_toolkit.lexers
import re



def transfer_to_agent_b():
        return agent_b


agent_b = Agent(
    name="Agent B",
    instructions="Only speak in Haikus.",
)

app = typer.Typer()
console = Console()

class DialogueStyle:
    ASSISTANT_COLOR = "green"
    SYSTEM_COLOR = "yellow"
    USER_COLOR = "blue"

class AgentCLI:
    def __init__(self):
        self.console = Console()
        self.history = []

        def greet(context_variables, language):
            user_name = context_variables["user_name"]
            greeting = "Hola" if language.lower() == "spanish" else "Hello"
            print(f"{greeting}, {user_name}!")
            return "Done"

        self.agent = Agent(name="Agent A", instructions="You are a helpful agent.", functions=[greet])
        self.client = Swarm()

    def display_message(self, role: str, content: str, thinking: bool = False):
        """Display a message with dialogue style for all roles"""
        text = Text()

        if role == "assistant":
            text.append("\n💡 Assistant • ", style=DialogueStyle.ASSISTANT_COLOR)
            text.append(time.strftime("%H:%M", time.localtime()), style="dim")
            text.append(f"\n{content}", style=DialogueStyle.ASSISTANT_COLOR)
            self.console.print(text)
        elif role == "system":
            text.append("\n⚙️  System • ", style=DialogueStyle.SYSTEM_COLOR)
            text.append(time.strftime("%H:%M", time.localtime()), style="dim")
            text.append(f"\n{content}\n", style=DialogueStyle.SYSTEM_COLOR)
            self.console.print(text)
        else:  # user
            text.append("👤 You • ", style=DialogueStyle.USER_COLOR)
            text.append(time.strftime("%H:%M", time.localtime()), style="dim")
            self.console.print(text, end="\n")
            user_input = console.input("")
            return user_input

@app.command()
def chat(
    api_key: str = typer.Option(
        None, "--api-key", "-k",
        help="OpenAI API key. Can also be set via OPENAI_API_KEY environment variable."
    ),
    system_prompt: str = typer.Option(
        "You are a helpful InjectiveLab AI assistant.",
        "--system-prompt",
        "-s",
        help="System prompt to set the agent's behavior"
    )
):
    """Start an interactive chat session"""

    # Set up API key
    if api_key:
        openai.api_key = api_key
    elif os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
    else:
        console.print("[red]Error: OpenAI API key not provided[/red]")
        raise typer.Exit(1)

    agent = AgentCLI()
    client = Swarm()
    messages = [{"role": "system", "content": system_prompt}]

    # Welcome message
    agent.display_message(
        "system",
        "Welcome to the InjectiveLab AI Agent CLI!\nType 'exit' or press Ctrl+C to end the conversation."
    )

    while True:
        try:
            # Get user input with prefix displayed first
            user_input = agent.display_message("user", "")
            if not user_input:
                continue


            if user_input.lower() in ['exit', 'quit']:
                agent.display_message("system", "Goodbye! 👋")
                break

            # Add to messages
            messages.append({"role": "user", "content": user_input})

            # Get response
            with Live(auto_refresh=True) as live:
                response = client.run(agent=agent.agent, messages=messages)
                response_messages = response.messages

                if response_messages:
                    for message in response_messages:
                        agent.display_message(message["role"], message["content"])
                        messages.append({"role": "assistant", "content": message['content']})
                else:
                    continue

        except KeyboardInterrupt:
            agent.display_message("system", "Goodbye! 👋")
            break
        except Exception as e:
            agent.display_message("system", f"Error: {str(e)}")
            break

if __name__ == "__main__":
    app()
