# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
# Use --frozen to respect the lockfile
# Use --no-install-project to avoid installing the current project as a package
# This creates a virtual environment at /app/.venv
RUN uv sync --frozen --no-install-project

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY . .


# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
    

USER app


# Expose port for HTTP API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py"]