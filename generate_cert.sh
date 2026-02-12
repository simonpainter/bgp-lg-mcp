#!/usr/bin/env bash
# Generate self-signed certificate for local development

openssl req -x509 -newkey rsa:2048 -nodes -out cert.pem -keyout key.pem -days 365 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"

echo "✓ Generated self-signed certificate"
echo "  Certificate: cert.pem"
echo "  Private key: key.pem"
echo ""
echo "Run HTTPS server with:"
echo "  python server.py --ssl-cert cert.pem --ssl-key key.pem"
