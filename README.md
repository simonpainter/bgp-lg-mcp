# BGP Looking Glass MCP Server

Query live BGP routing information from public route servers via Claude Desktop or any MCP client.

## What Is This?

A **BGP Looking Glass** is an internet-accessible service that exposes BGP (Border Gateway Protocol) routing data. BGP is the protocol that powers the internet's routing infrastructure. Looking glasses let you see what routes a particular BGP speaker has learned and how it would route traffic to a given destination.

This project wraps 7 public RouteViews servers into an **MCP (Model Context Protocol) server**, making BGP queries available to Claude Desktop and other AI assistants. Now you can ask Claude about internet routing with live, authoritative data.

**Example questions Claude can answer:**
- "What's the AS path to 8.8.8.0/24?"
- "Is this prefix routed?"
- "How many BGP neighbors does the Linx route server have?"
- "Compare routes to 1.1.1.1 across different regions"

## Features

- **Query live BGP routes** from 7 globally-distributed public route servers
- **Retrieve BGP summary statistics** including router ID, AS number, neighbor count
- **IPv4 and IPv6 support** - works with both address families
- **CIDR notation support** - look up entire subnets
- **Public IP validation** - blocks private/reserved address ranges for safety
- **Simple, fast setup** - works with Claude Desktop in minutes
- **Direct telnet connections** - no heavy dependencies or complex infrastructure
- **Real-time data** - queries live BGP data from public route servers

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure Claude Desktop

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bgp-lg": {
      "command": "python3",
      "args": ["/path/to/bgp-lg-mcp/server.py", "--stdio"]
    }
  }
}
```

### 3. Restart Claude Desktop

The BGP Looking Glass tools will appear in your MCP tools list. Start asking about BGP!

## Available Tools

### `route_lookup` - Query BGP Routes

Look up how a specific IP address or subnet would be routed.

**Parameters:**
- `destination` - IPv4/IPv6 address or CIDR subnet (e.g., `8.8.8.0/24`)
- `server` - Which route server to query (default: RouteViews Linx)

**Returns:** Raw BGP lookup output including matching routes, AS paths, next-hop information, and route attributes.

**Example:**
```
route_lookup(destination="1.1.1.1")
route_lookup(destination="2001:4860:4860::8888", server="RouteViews Sydney")
```

---

### `bgp_summary` - Get Router Statistics

Retrieve BGP summary information from a route server.

**Parameters:**
- `server` - Which route server to query (default: RouteViews Linx)

**Returns:** BGP summary output showing:
- Router BGP ID and AS number
- Number of learned routes (RIB entries)
- Total BGP neighbors and their status
- Detailed neighbor table with peer information, session uptime, and prefix counts

**Example:**
```
bgp_summary()
bgp_summary(server="RouteViews Equinix")
```

**Use cases:**
- Verify a route server is healthy
- Monitor BGP session status with major networks
- See which peers are actively advertising routes

---

### `list_servers` - Show Available Servers

Display all configured BGP looking-glass servers.

**Returns:** Server names, status (enabled/disabled), hostnames, and connection method.

**Example:**
```
list_servers()
```

## Supported Route Servers

7 globally-distributed public RouteViews servers, all freely accessible:

| Server | Location | Response Time | Coverage |
|--------|----------|---------------|----------|
| RouteViews Linx | London, UK | ~50ms | ⚡ **Fastest - use by default** |
| RouteViews Equinix | Multiple locations | ~330ms | Good alternative |
| RouteViews ISC | Multiple locations | ~530ms | Good alternative |
| RouteViews Main | Oregon, USA | ~740ms | Largest BGP view |
| RouteViews WIDE | Tokyo, Japan | ~1.1s | Asia-Pacific coverage |
| RouteViews Chicago | Chicago, USA | Variable | North America |
| RouteViews Sydney | Sydney, Australia | Variable | Oceania coverage |

All servers are:
- ✅ Publicly accessible (no registration required)
- ✅ Freely available 24/7
- ✅ Updated in real-time from BGP feeds
- ✅ Maintained by the University of Oregon Route Views Project

## Configuration

Edit `config.json` to modify route servers or add new ones:

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

- **name** - Server identifier (used when specifying which server to query)
- **host** - Hostname or IP address of the BGP router
- **port** - Telnet port (almost always 23)
- **connection_method** - Currently "telnet"; SSH support can be added
- **username** - Login username (empty = anonymous access)
- **password** - Login password
- **prompt** - Command prompt indicator (used to detect when responses are complete)
- **timeout** - Connection timeout in seconds
- **enabled** - Enable/disable without removing from config

## Running the Server

### MCP Stdio Mode (Recommended for Claude Desktop)

```bash
python3 server.py --stdio
```

This is the default for Claude Desktop integration. The server runs in the background and communicates via stdin/stdout.

### Streamable-HTTP Mode

For web-based MCP clients or testing:

```bash
python3 server.py
```

Starts on `http://127.0.0.1:8000` with MCP endpoint at `/mcp`

Custom host/port:
```bash
python3 server.py --host 0.0.0.0 --port 8080
```

## How It Works

1. **You ask Claude a BGP question** - "What's the AS path to 1.1.1.1?"
2. **Claude calls the appropriate MCP tool** - `route_lookup` with your query
3. **The tool connects to a public route server** via telnet
4. **Executes the BGP command** - `show ip bgp <destination>`
5. **Returns the raw router output** to Claude
6. **Claude interprets and summarizes** the results for you

All communication uses simple on-demand telnet connections - no persistent sessions, no complex infrastructure.

## Examples

### Check if a subnet is routed

```
User: Is 203.0.113.0/24 currently routed to the internet?
Claude: route_lookup(destination="203.0.113.0/24")
Result: [Shows all routes matching that prefix from the route server]
Claude: Based on the BGP data, this subnet is being announced by AS65001 with these paths...
```

### Compare routing across regions

```
User: How does traffic to Google DNS (8.8.8.8) route from different regions?
Claude: Calls route_lookup for 8.8.8.8 with different servers
Claude: Shows how different route servers see the path to Google's infrastructure
```

### Monitor route server health

```
User: Is the Linx route server operating normally?
Claude: bgp_summary(server="RouteViews Linx")
Result: Shows 63 active BGP neighbors, millions of routes, healthy sessions
Claude: Yes, the Linx route server is operating normally with X neighbors...
```

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt` (FastAPI, uvicorn, mcp)

## Limitations

- **Telnet only** - Currently only supports telnet connections (RFC 854 compatible)
- **Public IPs only** - Private/reserved address ranges are blocked
- **No authentication required** - All configured servers are public and free
- **Query rate limited** - No specific rate limiting, but be respectful of public resources

## Contributing

Contributions welcome! Areas of interest:
- SSH support for servers that don't support telnet
- Additional public route servers
- Performance optimizations
- Additional BGP query types
- Better error handling and diagnostics

## License

MIT
