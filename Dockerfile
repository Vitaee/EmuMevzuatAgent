# Use specific Python version as requested
FROM python:3.12.9-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Helper to ensure uv uses system python
    UV_SYSTEM_PYTHON=1

# Install system dependencies (curl for healthchecks if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency file
COPY pyproject.toml .

# Install dependencies into system python
# usage of --system flag installs into the global site-packages
RUN uv pip install --system .

# Copy application code
COPY . .

# Create a non-root user and switch to it for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose the application port
EXPOSE 8000

# Run the application
# We use uvicorn directly since dependencies are installed in system python
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
