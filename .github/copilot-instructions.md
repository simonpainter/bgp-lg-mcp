# Copilot Instructions for bgp-lg-mcp

## Project Overview

This is a **BGP Looking Glass MCP Server** — a Python project that exposes live BGP routing data from 7 public RouteViews servers as [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools. It enables AI assistants like Claude Desktop to answer questions about internet routing in real time.

## Architecture

```
server.py          - MCP server entry point; defines the three MCP tools
bgp_client.py      - Async telnet client for connecting to BGP route servers
validation.py      - IP address and CIDR notation validation
config.json        - Route server definitions (host, port, credentials, prompt)
session_manager.py - (legacy) Session management utilities
pyproject.toml     - Project metadata and dependencies
```

### MCP Tools Exposed

- **`route_lookup(destination, server)`** — Run `show ip bgp <destination>` on a route server
- **`bgp_summary(server)`** — Run `show ip bgp summary` on a route server
- **`list_servers()`** — List all configured servers from `config.json`

### Connection Flow

1. Load server config from `config.json`
2. Open an async telnet connection via `BGPTelnetClient`
3. Handle telnet protocol negotiation (IAC sequences)
4. Authenticate if credentials are configured
5. Send BGP command and read until the router prompt is detected
6. Return the raw router output to the MCP caller

## Tech Stack

- **Python 3.10+**
- **`mcp` Python SDK (`mcp>=1.0.0`)** — MCP server framework
- **FastAPI + uvicorn** — Optional HTTP REST API mode
- **asyncio** — All I/O is async; use `async`/`await` consistently
- **uv** — Preferred package manager (lockfile at `uv.lock`)

## Development Setup

```bash
# Install dependencies
pip install -e .

# Run in MCP stdio mode (for Claude Desktop)
python3 server.py --stdio

# Run as streamable-HTTP MCP server (default)
python3 server.py

# Run as plain HTTP REST API
python3 server.py --http-only
```

## Code Style

- Follow existing patterns: type hints on all function signatures, docstrings on all public functions/methods (Google style: Args/Returns)
- Use `logger = logging.getLogger(__name__)` in each module; log with `logger.info/debug/warning/error`
- Use `ValueError` for configuration/validation errors. `BGPTelnetClient.connect()` may raise `ConnectionError` on connection failures, but `query_bgp_server()` currently wraps all exceptions into `RuntimeError`, so MCP tool handlers should expect to catch `ValueError` for bad input and `RuntimeError` for any query/connection failure.
- All network I/O must be `async`; do not use blocking calls
- Validate all user-supplied IP addresses and CIDR prefixes with `validate_ip_or_cidr()` from `validation.py` before querying servers
- Only public IP addresses are permitted; private, loopback, and link-local ranges are rejected

## Adding a New Route Server

1. Add an entry to `config.json` with `name`, `host`, `port`, `prompt`, `timeout`, and `enabled`
2. No code changes are needed — the server list is loaded dynamically from config

## Testing

There is no automated test suite yet. Validate changes manually:

```bash
# Verify tool execution end-to-end
python3 server.py --stdio
```

When adding new features, write tests consistent with standard `pytest` patterns and place them in a `tests/` directory.

## Key Constraints

- **Telnet only** — only telnet connections are currently supported; no SSH
- **Public IPs only** — private/reserved ranges are blocked in `validation.py`
- **No persistent sessions** — each tool call opens and closes a fresh telnet connection
- **Config-driven** — all server parameters live in `config.json`; avoid hard-coding hostnames or credentials in source files
