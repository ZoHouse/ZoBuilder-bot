#!/bin/bash
set -e

# Start the Telegram Bot in the background
echo "Starting Telegram Bot..."
uv run python bot.py &

# Start the Webhook Server in the foreground
# Railway provides the PORT environment variable
echo "Starting Webhook Server on port $PORT..."
uv run uvicorn webhooks:app --host 0.0.0.0 --port ${PORT:-8000}
