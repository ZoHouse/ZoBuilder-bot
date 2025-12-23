# Use a Python image with uv pre-installed or install it
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy uv configuration files first
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures we use exact versions from uv.lock
# --no-install-project skips installing the project itself as a package (if not needed) or we install it later
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . .

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Make start script executable
RUN chmod +x start.sh

CMD ["./start.sh"]
