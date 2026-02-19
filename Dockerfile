# Django API service Dockerfile
# Used by Railway for the backend service

FROM python:3.14-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY backend/ .

# Collect static files
RUN DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=build-placeholder \
    DEBUG=false \
    uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Default CMD; Railway overrides via startCommand in railway.toml
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--workers", "2"]
