#!/usr/bin/env bash
# Quick start script for BGP Looking Glass MCP Server with HTTPS

set -e

echo "🚀 BGP Looking Glass MCP Server"
echo "================================"
echo ""

# Check if certificates exist
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "📝 Generating self-signed certificates..."
    ./generate_cert.sh
    echo ""
fi

# Display configuration options
echo "Available startup options:"
echo ""
echo "1️⃣  MCP Stdio Mode (RECOMMENDED for Claude Desktop)"
echo "   python server.py --stdio"
echo ""
echo "2️⃣  HTTPS Streamable-HTTP Mode"
echo "   python server.py --ssl-cert cert.pem --ssl-key key.pem"
echo ""
echo "3️⃣  HTTP REST API Mode (localhost only)"
echo "   python server.py --http-only"
echo ""
echo "⚠️  Important: Claude Desktop works best with stdio mode!"
echo ""
echo "Starting in MCP Stdio Mode..."
echo "Press Ctrl+C to stop"
echo ""

# Start server in stdio mode (best for Claude Desktop)
exec python server.py --stdio
