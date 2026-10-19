# docker build -t fastapi-app .
# docker run -p 8080:8080 --env-file .env fastapi-app

# BUILD STAGE
FROM python:3.14.4-slim-bookworm AS builder

# Copy UV binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.11.5 /uv /uvx /bin/

WORKDIR /app

# UV Docker optimizations
ENV UV_COMPILER_BYTECODE=1
ENV UV_LINK_MODE=copy
# Use python from the base image, don't download a new python
ENV UV_PYTHON_DOWNLOADS=0

# Placing pyproject.toml and uv.lock higher up then the project
# makes docker builds a layer just for them,
# avoiding the need to build it again if there were only conde changes
# Install depencencies first (cached if unchanged)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

# Copy app code and install project
COPY . ./
RUN uv sync --locked --no-dev

# PRODUCTION STAGE
FROM python:3.14.4-slim-bookworm

WORKDIR /app

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Copy app and dependencies from builder stage
COPY --from=builder --chown=appuser:appuser /app /app

# run fastapi and python without the full path
ENV PATH="/app/.venv/bin:$PATH"
# makes prints and logs shows up imidiatally
ENV PYTHONUNBUFFERED=1
# for local testing
ENV PORT=8080

# exec replaces shell so fastapi recives SIGTERM for clean shutdown
# CMD ["/bin/sh", "-c", "exec fastapi run --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips '*'"]
CMD ["/bin/sh", "-c", "exec python -m fastapi run --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips '*'"]