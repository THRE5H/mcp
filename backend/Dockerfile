FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

# Install the backend dependency set while building from the repository root.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the whole repository because the backend imports shared root modules.
COPY . /app

ENV PYTHONPATH=/app
WORKDIR /app/backend

CMD ["sh", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
