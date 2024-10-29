import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
import openai
import os
from typing import Optional
from swarm import Swarm, Agent
import time

app = typer.Typer()
console = Console()

def pretty_print_messages(messages):
    for message in messages:
        if message["content"] is None:
            continue
        print(f"{message['sender']}: {message['content']}")

class AgentCLI:
    def __init__(self):
        self.console = Console()
        self.history = []
        self.agent = Agent(name="AI Agent",    instructions="You are a helpful agent.",)
        self.client = Swarm()

    def display_message(self, role: str, content: str):
        """Display a message with appropriate styling"""
        if role == "assistant":
            panel = Panel(
                Markdown(content),
                title="🤖 Assistant",
                border_style="green",
                padding=(1, 2)
            )
        else:
            panel = Panel(
                content,
                title="👤 You",
                border_style="blue",
                padding=(1, 2)
            )
        self.console.print(panel)
        self.console.print()


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
    """Start an interactive chat session with the InjectiveLab AI agent"""

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
    console.print(Panel(
        "[bold green]Welcome to the InjectiveLab AI Agent CLI![/bold green]\n"
        "Type 'exit' or press Ctrl+C to end the conversation.",
        title="🤖 InjectiveLab Agent",
        border_style="green"
    ))

    while True:
        try:
            # Get user input
            user_input = typer.prompt("\nYou")
            # Display user message
            agent.display_message("user", user_input)

            if user_input.lower() in ['exit', 'quit']:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break

            # Add to messages
            messages.append({"role": "user", "content": user_input})

            # Get and display assistant response
            response = client.run(agent=agent.agent, messages=messages)
            response_messages = response.messages
            if response_messages:
                for message in response_messages:
                    agent.display_message(message["role"], message["content"])
                    messages.append({"role": "assistant", "content": message['content']})
            else:
                continue

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye! 👋[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            break

if __name__ == "__main__":
    app()
