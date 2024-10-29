# agent.py
from swarm import Swarm, Agent
import os

# Set up OpenAI client
client = Swarm()

# Define the agent
agent = Agent(
    name="Agent",
    instructions="You are a helpful assistant ready to answer questions."
)

# Run the agent on a prompt
response = client.run(
    agent=agent,
    messages=[{"role": "user", "content": "Hello, how can you help me?"}]
)

print(response.messages[-1]["content"])
