# bgp-lg-mcp

A BGP Looking Glass MCP (Model Context Protocol) server that allows you to query BGP routes from various looking-glass servers.

## Features

- Query BGP routes from multiple looking-glass servers
- Support for IPv4 and IPv6 addresses
- CIDR subnet notation support
- Validation of public IP addresses (blocks private/reserved ranges)
- Telnet-based connection to BGP servers
- Configurable server list with credentials

## Installation

```bash
pip install -e .
```

Or using uv:

```bash
uv pip install -e .
```

## Configuration

Configure your BGP looking-glass servers in `config.json`:

```json
{
  "servers": [
    {
      "name": "route-server.ip.att.net",
      "host": "route-server.ip.att.net",
      "port": 23,
      "connection_method": "telnet",
      "username": "rviews",
      "password": "rviews",
      "prompt": "route-server#",
      "timeout": 10,
      "enabled": true
    }
  ]
}
```

### Server Configuration Fields

- **name**: Unique identifier for the server (used when querying)
- **host**: Hostname or IP address
- **port**: Telnet port (default: 23)
- **connection_method**: Connection protocol (currently "telnet")
- **username**: Login username (optional)
- **password**: Login password (optional)
- **prompt**: Command prompt indicator for detecting when to read response
- **timeout**: Connection timeout in seconds (default: 10)
- **enabled**: Boolean to enable/disable the server (default: true)

## Usage

### Running the HTTP Server (Default)

```bash
python server.py
```

The server will start on `http://127.0.0.1:8000` by default.

**Custom host and port:**
```bash
python server.py --host 0.0.0.0 --port 8080
```

**Interactive API documentation:**
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Running in MCP Stdio Mode

For use with MCP-compatible clients (Claude Desktop, etc.):

```bash
python server.py --stdio
```

### After Installation

```bash
bgp-lg-mcp                    # Run HTTP server
bgp-lg-mcp --stdio            # Run in MCP mode
bgp-lg-mcp --host 0.0.0.0 --port 3000  # Custom host/port
```

## HTTP API Endpoints

### Health Check
```
GET /health
```

Returns server status.

### Route Lookup
```
POST /route-lookup?destination=1.1.1.1&server=route-server.ip.att.net
```

Query a route on a BGP looking-glass server.

**Query Parameters:**
- `destination` (required): IPv4/IPv6 address or CIDR subnet
- `server` (optional): BGP server name (default: `route-server.ip.att.net`)

**Response:**
```json
{
  "destination": "1.1.1.1",
  "server": "route-server.ip.att.net",
  "result": "... BGP server response ..."
}
```

### List Servers
```
GET /servers
```

Get configuration for all available servers.

**Response:**
```json
{
  "servers": [
    {
      "name": "route-server.ip.att.net",
      "host": "route-server.ip.att.net",
      "port": 23,
      "connection_method": "telnet",
      ...
    }
  ]
}
```

## MCP Integration (Stdio Mode)

When running in MCP stdio mode (`--stdio`), the following tools are available to MCP clients like Claude Desktop:

### MCP Tools

#### `route_lookup`

Look up a route on a BGP looking-glass server.

**Parameters:**
- `destination` (required): IPv4 address (e.g., `1.1.1.1`), IPv6 address, or CIDR subnet (e.g., `1.1.1.0/24`)
- `server` (optional): Name of the BGP server to query (default: `route-server.ip.att.net`)

**Example:**
```
route_lookup(destination="1.1.1.1")
route_lookup(destination="8.8.8.0/24", server="route-server.ip.att.net")
route_lookup(destination="2001:4860:4860::8888")
```

**Validation:**
- Validates that the IP address is public (not private, loopback, or link-local)
- Supports both IPv4 and IPv6 addresses
- Supports CIDR notation for subnets

#### `list_servers`

List all configured BGP looking-glass servers.

**Returns:** Information about all available servers including their status, host, and connection method.

### MCP Configuration for Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

## Supported Looking-Glass Servers

Currently configured:
- **route-server.ip.att.net** (AT&T - rviews account)

Additional servers can be added to the `config.json` file.

## Common Looking-Glass Servers

Some public BGP looking-glass servers that can be added:

- **route-server.ip.att.net** - AT&T route server
- **route-views.routeviews.org** - University of Oregon Route Views
- **route-views2.routeviews.org** - Route Views Secondary
- **route-views3.routeviews.org** - Route Views Route Server #3
- **route-views6.routeviews.org** - Route Views IPv6

## License

MIT

