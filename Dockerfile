FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY server/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ /app/

# Port exposed
EXPOSE 8000

# Run using Daphne ASGI server for WebSocket support
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "cogniroute.asgi:application"]
