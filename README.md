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

### HTTPS Mode (Required by Claude Desktop)

Claude Desktop requires HTTPS connections for MCP servers. Generate a self-signed certificate:

```bash
./generate_cert.sh
```

This creates `cert.pem` and `key.pem` in the current directory.

Then run the server with HTTPS:

```bash
python server.py --ssl-cert cert.pem --ssl-key key.pem
```

Or with custom host/port:

```bash
python server.py --ssl-cert cert.pem --ssl-key key.pem --host 0.0.0.0 --port 8443
```

The server will start on `https://127.0.0.1:8000` with the MCP endpoint at `https://127.0.0.1:8000/mcp`

**Note:** Claude Desktop may warn about the self-signed certificate, which is normal for development. You can safely proceed.

### Using Production Certificates

For production deployments, use certificates from a trusted CA (e.g., Let's Encrypt):

```bash
python server.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

## HTTP/HTTPS Endpoints

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

### ⚡ Quickest Setup (Recommended)

Use **stdio mode** - no HTTPS needed, no server to run:

```bash
./start-server.sh
```

Or manually:

```bash
python server.py --stdio
```

Then add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

Restart Claude Desktop and the tools will appear in your MCP tools list.

---

### Advanced: Streamable-HTTP with HTTPS

If you need to run a separate server (streamable-http transport), HTTPS is required. However, **Claude Desktop has strict SSL certificate validation** and won't accept self-signed certificates for remote connections.

**Options:**

1. **Use a proper CA-signed certificate** (production):
   ```bash
   python server.py --ssl-cert /path/to/ca-signed-cert.pem --ssl-key /path/to/ca-key.pem
   ```
   Then add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "bgp-lg": {
         "url": "https://your-domain.com:8000/mcp",
         "transport": "sse"
       }
     }
   }
   ```

2. **Use mkcert for trusted self-signed certificates** (development):
   ```bash
   # Install mkcert: https://github.com/FiloSottile/mkcert
   mkcert localhost 127.0.0.1
   python server.py --ssl-cert localhost.pem --ssl-key localhost-key.pem
   ```
   Then add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "bgp-lg": {
         "url": "https://localhost:8000/mcp",
         "transport": "sse"
       }
     }
   }
   ```

3. **Stick with stdio mode** (simplest and recommended):
   No HTTPS, no certificate issues, instant setup.

---

### Restart Claude Desktop

After updating the config, restart Claude Desktop. The BGP Looking Glass tools will appear in your MCP tools list.

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

## Troubleshooting

### "Connection Error - Check if your MCP server is running and proxy token is correct"

**Solution:** Use **stdio mode** instead of streamable-http:
```bash
python server.py --stdio
```

The error typically occurs with streamable-http because Claude Desktop strictly validates SSL certificates and won't accept self-signed certificates.

### HTTPS doesn't work with Claude Desktop

**Reason:** Claude Desktop requires certificates signed by a trusted Certificate Authority for remote/streamable-http connections.

**Solutions:**
1. Use stdio mode (no HTTPS needed) - **recommended**
2. Use mkcert to create trusted development certificates
3. Use a proper CA-signed certificate for production

See the "Claude Desktop Integration" section above for detailed setup.

### Server won't start

**Check:**
- Python 3.7+ is installed
- All dependencies are installed: `pip install -e .`
- Port 8000 isn't in use: `lsof -i :8000` (macOS/Linux)
- Certificate files exist if using HTTPS: `ls -la *.pem`

### Route lookup returns empty results

**Check:**
- The destination IP is public (not 10.x.x.x, 192.168.x.x, etc.)
- The server is reachable: `telnet route-views.linx.routeviews.org 23`
- Try a different server in case one is down
- Check server logs for error details

## Development

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
