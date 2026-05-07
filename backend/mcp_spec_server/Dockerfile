FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment variables
ENV MCP_SERVER_HOST=0.0.0.0
ENV BACKEND_URL=http://backend:8000

# Run server
CMD ["sh", "-lc", "uvicorn http_server:app --host 0.0.0.0 --port ${PORT:-8001}"]
