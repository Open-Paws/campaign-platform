FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir .

# Application code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Create data directory for SQLite
RUN mkdir -p /data

ENV DATABASE_URL="sqlite:////data/campaign_platform.db"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run with uvicorn
CMD ["uvicorn", "platform.dashboard.api:app", "--host", "0.0.0.0", "--port", "8000"]
