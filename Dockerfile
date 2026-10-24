FROM python:3.12-slim

WORKDIR /app

# install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY Agentic_assistant ./Agentic_assistant

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# run uvicorn properly on 0.0.0.0:8000
CMD ["bash", "-c", "python Agentic_assistant/mcp_servers/tools_server.py & uvicorn Agentic_assistant.router.main:app --host 0.0.0.0 --port 8000 --workers 2"]