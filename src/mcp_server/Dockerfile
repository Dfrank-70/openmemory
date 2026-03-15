FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY kb ./kb
COPY .env.example ./.env.example

ENV PYTHONPATH=/app

CMD ["python", "-m", "src.mcp_server.server"]
