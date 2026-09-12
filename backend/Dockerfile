# Stage 1: Build & Dependency Stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Hardened Production Runtime Stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime system libraries (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /install /usr/local

# Create non-root system user for production process isolation
RUN useradd -m -u 10001 -s /bin/bash roadsos && \
    mkdir -p /app/static/uploads /app/data && \
    chown -R roadsos:roadsos /app

# Copy application source code
COPY --chown=roadsos:roadsos . /app

# Make startup script executable
RUN chmod +x /app/start.sh

# Security & Runtime Environment Settings
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

USER roadsos

EXPOSE 8000

CMD ["/app/start.sh"]
