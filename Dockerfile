# Base image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building wheels (lxml) and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# App source
COPY . .

# Entrypoint for running migrations + starting services
RUN chmod +x /app/scripts/docker_entrypoint.sh

EXPOSE 8000 8501

ENTRYPOINT ["/app/scripts/docker_entrypoint.sh"]

# Default command (docker-compose overrides for api/worker)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
