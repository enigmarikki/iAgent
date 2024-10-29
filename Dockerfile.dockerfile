# Use a Python base image
FROM python:3.10-slim

# Set up working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent script
COPY agent.py .

# Run the agent script
CMD ["python", "agent.py"]
