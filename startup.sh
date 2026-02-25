#!/bin/bash
# Azure App Service startup script for BGP Looking Glass MCP Server

# Exit on any error
set -e

# Log startup
echo "Starting BGP Looking Glass MCP Server..."

# Install/update dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start the server with Gunicorn + Uvicorn
# Configuration:
# - -w 1: Single worker process (suitable for small instances)
#         Increase to match your Azure App Service instance size
# - -k uvicorn.workers.UvicornWorker: Use Uvicorn worker for async support
# - main:application: Load the 'application' ASGI app from main.py
# - --bind 0.0.0.0:8000: Listen on all interfaces on port 8000
# - --timeout 300: 5 minute timeout for long-running BGP queries
# - --access-logfile -: Log to stdout for Azure monitoring
echo "Starting Gunicorn server..."
exec gunicorn \
    -w 1 \
    -k uvicorn.workers.UvicornWorker \
    server:application \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
