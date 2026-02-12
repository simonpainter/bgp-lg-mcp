# BGP Looking Glass MCP Server

A fast, lightweight BGP Looking Glass MCP (Model Context Protocol) server that queries BGP route information from multiple public RouteViews servers via simple on-demand telnet connections.

## Features

- **Fast BGP queries** - RouteViews Linx responds in ~50ms
- **Query BGP routes** from 7 configured RouteViews servers globally
- **BGP summary statistics** - View router info, AS number, and neighbor status
- **IPv4 and IPv6 support** - Query both address families
- **CIDR notation support** - Look up entire subnets (e.g., `1.1.1.0/24`)
- **Public IP validation** - Blocks private/reserved address ranges
- **Simple on-demand connections** - No session persistence overhead
- **Multiple transport modes** - MCP stdio, streamable-http, or REST API
- **Configurable servers** - Easy to add/remove looking-glass servers

## How It Works

The server uses **simple on-demand connections** to public RouteViews servers:
1. Creates a new telnet connection when a query is made
2. Executes the BGP command (e.g., `show ip bgp <destination>`)
3. Returns the raw router output
4. Closes the connection

This approach is fast enough for RouteViews servers (typical response: 0.5-1.5s per query including connection time) and avoids the complexity of persistent session management.

## Available Tools

### `route_lookup` - Look Up BGP Routes

Query a specific IP address or subnet on a BGP looking-glass server.

**Parameters:**
- `destination` (required): IPv4 address (e.g., `1.1.1.1`), IPv6 address (e.g., `2001:4860:4860::8888`), or CIDR subnet (e.g., `1.1.1.0/24`)
- `server` (optional): BGP server to query. Options:
  - `RouteViews Linx` ⚡ Default - fastest (~50ms)
  - `RouteViews Equinix` (~330ms)
  - `RouteViews ISC` (~530ms)
  - `RouteViews Main` (~740ms)
  - `RouteViews WIDE` (~1.1s)
  - `RouteViews Chicago`
  - `RouteViews Sydney` (global coverage)

**What it returns:**
Raw BGP route lookup output showing:
- Matching routes and next-hop information
- AS path details
- Route attributes
- Community information
- Prefix information

**Example usage:**
```
route_lookup(destination="1.1.1.1")
route_lookup(destination="8.8.8.0/24", server="RouteViews Equinix")
route_lookup(destination="2001:4860:4860::8888", server="RouteViews Sydney")
```

**Validation:**
- Ensures destination is a public IP (blocks private ranges like 10.x.x.x, 192.168.x.x)
- Supports CIDR notation (/24, /32, etc.)
- Works with both IPv4 and IPv6

---

### `bgp_summary` - Get BGP Router Statistics

Retrieve BGP summary information from a route server, showing router details and BGP neighbor status.

**Parameters:**
- `server` (optional): BGP server to query (same options as `route_lookup`; default: RouteViews Linx)

**What it returns:**
BGP summary output showing:
- **Router Identifier** - BGP router ID
- **Local AS Number** - The autonomous system number
- **RIB Statistics** - Number of routes and memory usage
- **Neighbor Count** - Total number of BGP peers
- **Detailed neighbor table** with:
  - Neighbor IP address and AS number
  - Messages received/sent
  - Session uptime
  - Prefixes received and sent
  - Neighbor description/name

**Example usage:**
```
bgp_summary()
bgp_summary(server="RouteViews Equinix")
```

**Use cases:**
- Check if a route server is healthy and connected
- See how many neighbors a route server has
- Monitor which peers are actively advertising routes
- Verify session status with specific networks

---

### `list_servers` - Show Available Servers

List all configured BGP looking-glass servers and their details.

**Parameters:** None

**What it returns:**
- Server name and status (enabled/disabled)
- Hostname/IP address and port
- Connection method

**Example usage:**
```
list_servers()
```

## Installation

### Using pip

```bash
pip install -e .
```

### Using uv

```bash
uv pip install -e .
```

## Configuration

BGP servers are configured in `config.json`:

```json
{
  "servers": [
    {
      "name": "RouteViews Linx",
      "host": "route-views.linx.routeviews.org",
      "port": 23,
      "connection_method": "telnet",
      "username": "",
      "password": "",
      "prompt": ">",
      "timeout": 15,
      "enabled": true
    }
  ]
}
```

### Configuration Fields

- **name** - Server identifier (used in tool parameters)
- **host** - Hostname or IP address
- **port** - Telnet port (default: 23)
- **connection_method** - Currently "telnet" (SSH support coming)
- **username** - Login username (empty for anonymous access)
- **password** - Login password (empty if not required)
- **prompt** - Command prompt indicator (e.g., `>`, `#`)
- **timeout** - Connection timeout in seconds (default: 15)
- **enabled** - Toggle server availability (true/false)

## Running the Server

### Default Mode (Streamable-HTTP)

Best for web-based MCP clients:

```bash
python server.py
```

Starts on `http://127.0.0.1:8000` with MCP endpoint at `/mcp`

### Custom Host/Port

```bash
python server.py --host 0.0.0.0 --port 8080
```

### MCP Stdio Mode

For Claude Desktop and other stdio-compatible MCP clients:

```bash
python server.py --stdio
```

### REST API Mode

Plain HTTP API without MCP protocol:

```bash
python server.py --http-only
```

## HTTP Endpoints

### Health Check

```
GET /health
```

Returns server status.

### MCP Streamable-HTTP

```
POST /mcp
```

Main MCP protocol endpoint for web-based clients.

### Route Lookup (REST API)

```
POST /route-lookup?destination=1.1.1.1&server=RouteViews%20Linx
```

Query parameters:
- `destination` (required) - IPv4/IPv6 address or CIDR subnet
- `server` (optional) - Server name (default: RouteViews Linx)

Response:
```json
{
  "destination": "1.1.1.1",
  "server": "RouteViews Linx",
  "result": "... BGP route output ..."
}
```

### List Servers (REST API)

```
GET /servers
```

Returns all configured servers and their details.

## Claude Desktop Integration

To use with Claude Desktop, add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bgp-lg": {
      "command": "python",
      "args": ["/path/to/bgp-lg-mcp/server.py", "--stdio"]
    }
  }
}
```

Then restart Claude Desktop. The tools will appear in the MCP tools list.

## Supported Servers

The server comes pre-configured with 7 RouteViews servers:

| Server | Location | Response Time | Notes |
|--------|----------|---------------|-------|
| RouteViews Linx | London, UK | ~50ms | ⚡ **Fastest** - Use this by default |
| RouteViews Equinix | Various | ~330ms | Good alternative |
| RouteViews ISC | Various | ~530ms | Good alternative |
| RouteViews Main | Oregon, USA | ~740ms | Largest BGP view |
| RouteViews WIDE | Tokyo, Japan | ~1.1s | Asia-Pacific coverage |
| RouteViews Chicago | Chicago, USA | Variable | North America |
| RouteViews Sydney | Sydney, Australia | Variable | Oceania coverage |

All servers are:
- Publicly accessible (no special registration required)
- Running Cisco IOS-XR with `show ip bgp` command support
- Updated in real-time from global BGP feeds
- Maintained by the University of Oregon Route Views Project

### Adding More Servers

To add a new looking-glass server, add an entry to `config.json`:

```json
{
  "name": "Server Name",
  "host": "route-server.example.com",
  "port": 23,
  "connection_method": "telnet",
  "username": "optional_username",
  "password": "optional_password",
  "prompt": ">",
  "timeout": 15,
  "enabled": true
}
```

## Performance

- **Connection time**: 50ms - 1.1s depending on server
- **Command execution**: Typically <500ms
- **Total query time**: 0.5s - 1.5s per query

No startup delay or connection pre-warming needed.

## Development

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

## Common BGP Queries

### Check if a prefix is routed

```
route_lookup(destination="8.8.8.0/24")
```

### Monitor a large provider's health

```
bgp_summary(server="RouteViews Equinix")
```

### Compare routes across regions

```
route_lookup(destination="1.1.1.1", server="RouteViews Linx")
route_lookup(destination="1.1.1.1", server="RouteViews Sydney")
```

### Check IPv6 routing

```
route_lookup(destination="2001:4860:4860::8888")
```

## License

MIT
