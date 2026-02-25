# BGP Looking Glass MCP Server

Query live BGP routing information, ping IP addresses, and trace network paths from public route servers via Claude Desktop or any MCP client.

## What Is This?

A **BGP Looking Glass** is an internet-accessible service that exposes BGP (Border Gateway Protocol) routing data. BGP is the protocol that powers the internet's routing infrastructure. Looking glasses let you see what routes a particular BGP speaker has learned and how it would route traffic to a given destination.

This project wraps 7 public RouteViews servers into an **MCP (Model Context Protocol) server**, making BGP queries, ping, and traceroute available to Claude Desktop and other AI assistants. Now you can ask Claude about internet routing with live, authoritative data.

**Example questions Claude can answer:**

- "What's the AS path to 8.8.0/24?"
- "Is this prefix routed?"
- "How many BGP neighbors does the Linx route server have?"
- "Who owns AS15169?"
- "Which country is IP 1.1.1.1 located in?"
- "Can you ping 8.8.8.8 from different servers and compare latencies?"
- "Show me the network path to Google DNS"
- "Compare routes to 1.1.1.1 across different regions"

## Features

- **Query live BGP routes** from 7 globally-distributed public route servers
- **Ping IP addresses** from route servers to test connectivity and measure latency
- **Trace routes** to IP addresses to see the network path and identify which ASes are involved
- **Look up IP geolocation & BGP metadata** using BGPKit public API
- **Look up ASN ownership** using BGPKit public API
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

### JSON Response Format

All tools support both **text** (default) and **JSON** response formats for flexibility in how you consume data.

**Using JSON format:**

```python
# Get structured JSON instead of text
route_lookup(destination="8.8.8.0/24", format="json")
bgp_summary(format="json")
asn_owner(asn="AS15169", format="json")
ip_lookup(ip="8.8.8.8", format="json")
list_servers(format="json")
```

**Benefits of JSON format:**

- **Programmatic parsing** - Easy to parse and process structured data
- **Type safety** - Pydantic models validate all responses
- **Consistent structure** - All tools follow the same JSON schema
- **Error handling** - Errors also return structured JSON
- **API integration** - Better for building on top of the MCP server

**Example JSON response:**

```json
{
  "type": "ip_lookup",
  "ip": "8.8.8.8",
  "country": "US",
  "asn": 15169,
  "prefix": "8.8.8.0/24",
  "name": "Google, YouTube (for Google Fiber see AS16591 record)",
  "rpki": "valid",
  "updated_at": "2026-02-25T10:00:00"
}
```

---

### `route_lookup` - Query BGP Routes

Look up how a specific IP address or subnet would be routed.

**Parameters:**

- `destination` - IPv4/IPv6 address or CIDR subnet (e.g., `8.8.8.0/24`)
- `server` - Which route server to query (default: RouteViews Linx)
- `format` - Response format: `text` (default) or `json`

**Returns:** Raw BGP lookup output including matching routes, AS paths, next-hop information, and route attributes (or structured JSON if format="json").

**Example:**

```python
route_lookup(destination="1.1.1.1")
route_lookup(destination="2001:4860:4860::8888", server="RouteViews Sydney")
route_lookup(destination="8.8.8.0/24", format="json")
```

---

### `bgp_summary` - Get Router Statistics

Retrieve BGP summary information from a route server.

**Parameters:**

- `server` - Which route server to query (default: RouteViews Linx)
- `format` - Response format: `text` (default) or `json`

**Returns:** BGP summary output showing:

- Router BGP ID and AS number
- Number of learned routes (RIB entries)
- Total BGP neighbors and their status
- Detailed neighbor table with peer information, session uptime, and prefix counts

**Example:**

```python
bgp_summary()
bgp_summary(server="RouteViews Equinix")
bgp_summary(format="json")
```

**Use cases:**

- Verify a route server is healthy
- Monitor BGP session status with major networks
- See which peers are actively advertising routes

---

### `list_servers` - Show Available Servers

Display all configured BGP looking-glass servers.

**Parameters:**

- `format` - Response format: `text` (default) or `json`

**Returns:** Server names, status (enabled/disabled), hostnames, and connection method.

**Example:**

```python
list_servers()
list_servers(format="json")
```

---

### `asn_owner` - Look Up ASN Owner

Retrieve the owner name for an Autonomous System Number (ASN) using BGPKit API.

**Parameters:**

- `asn` - Autonomous System Number in format "AS123" or "123" (e.g., "AS15169", "64512")
- `format` - Response format: `text` (default) or `json`

**Returns:** Owner name for the ASN.

**Example:**

```python
asn_owner(asn="AS15169")
asn_owner(asn="15169")
asn_owner(asn="AS64512")
asn_owner(asn="AS15169", format="json")
```

**JSON Example Response:**

```json
{
  "type": "asn_owner",
  "asn": "AS15169",
  "owner": "GOOGLE - Google LLC"
}
```

**Use cases:**

- Identify who operates a particular AS
- Verify AS ownership when analyzing routing information
- Understand the entities involved in a BGP path

---

### `ip_lookup` - Geolocation and BGP Metadata

Look up geolocation information and BGP metadata for an IP address using BGPKit API.

**Parameters:**

- `ip` - IPv4 or IPv6 address (e.g., `8.8.8.8` or `2001:4860:4860::8888`)
  - Must be a public address (private/reserved addresses are rejected for safety)
- `format` - Response format: `text` (default) or `json`

**Returns:** IP geolocation data including:

- **Country** - GeoIP country code
- **ASN** - Autonomous System Number announcing the IP
- **Prefix** - CIDR prefix covering the IP
- **Name** - Organization name (if available)
- **RPKI** - RPKI validation status (valid/invalid/unknown)
- **Updated** - Timestamp of last update

**Example:**

```python
ip_lookup(ip="8.8.8.8")
ip_lookup(ip="1.1.1.1")
ip_lookup(ip="2001:4860:4860::8888")
ip_lookup(ip="8.8.8.8", format="json")
```

**Text Output Example:**

```
IP Lookup: 8.8.8.8
Country: US
ASN: 15169
Prefix: 8.8.8.0/24
Name: Google, YouTube (for Google Fiber see AS16591 record)
RPKI Status: valid
Updated: 2026-02-25T10:00:00
```

**JSON Output Example:**

```json
{
  "type": "ip_lookup",
  "ip": "8.8.8.8",
  "country": "US",
  "asn": 15169,
  "prefix": "8.8.8.0/24",
  "name": "Google, YouTube (for Google Fiber see AS16591 record)",
  "rpki": "valid",
  "updated_at": "2026-02-25T10:00:00"
}
```

**Use cases:**

- Determine which country an IP address is located in
- Find which organization operates an IP
- Verify RPKI signing status of announced prefixes
- Map traffic sources to organizations
- Verify prefix ownership

---

### `ping_host` - Ping an IP Address

Ping an IP address from a BGP looking-glass server to test connectivity and measure round-trip time.

**Parameters:**

- `ip` - IPv4 or IPv6 address to ping (e.g., `8.8.8.8`, `1.1.1.1`)
- `server` - Which route server to use for pinging (default: RouteViews Linx)
- `format` - Response format: `text` (default) or `json`

**Returns:** Ping statistics including:

- **Success rate** - Percentage of successful pings (0-100%)
- **Packets sent/received** - Total packets and successfully returned packets
- **Round-trip times** - Minimum, average, and maximum latency in milliseconds

**Example:**

```python
ping_host(ip="8.8.8.8")
ping_host(ip="1.1.1.1", server="RouteViews Main")
ping_host(ip="2001:4860:4860::8888", format="json")
```

**Text Output Example:**

```
Ping Results for 8.8.8.8
Server: RouteViews Linx
Packets sent: 5
Packets received: 5
Success rate: 100%
Round-trip times (ms): min=10.5, avg=11.2, max=12.3
```

**JSON Output Example:**

```json
{
  "type": "ping",
  "ip": "8.8.8.8",
  "server": "RouteViews Linx",
  "stats": {
    "sent": 5,
    "received": 5,
    "success_rate": 100,
    "min_ms": 10.5,
    "avg_ms": 11.2,
    "max_ms": 12.3
  },
  "raw_output": "Success rate is 100 percent (5/5), round-trip min/avg/max = 10.5/11.2/12.3 ms"
}
```

**Supported Servers:**

- RouteViews Main ✅
- RouteViews Linx ❌ (command not available)
- RouteViews 2 ❌ (command not available)
- Other servers ❌ (limited access)

**Use cases:**

- Test connectivity to a remote IP address
- Measure latency from different geographic locations
- Verify if an IP address is reachable
- Diagnose network issues by comparing latency
- Monitor round-trip times over time

---

### `traceroute_host` - Trace Route to an IP Address

Trace the network path (hops) to an IP address from a BGP looking-glass server.

**Parameters:**

- `ip` - IPv4 or IPv6 address to trace (e.g., `8.8.8.8`, `1.1.1.1`)
- `server` - Which route server to use for tracing (default: RouteViews Linx)
- `format` - Response format: `text` (default) or `json`

**Returns:** Traceroute results including:

- **Hop number** - Sequential hop from source to destination
- **Hostname** - DNS name of the hop (if available)
- **IP address** - IP address of the hop
- **AS number** - Autonomous System number of the hop
- **Response times** - Round-trip time for each probe (typically 3 probes per hop)

**Example:**

```python
traceroute_host(ip="8.8.8.8")
traceroute_host(ip="1.1.1.1", server="RouteViews Sydney")
traceroute_host(ip="2001:4860:4860::8888", format="json")
```

**Text Output Example:**

```
Traceroute to 8.8.8.8
Server: RouteViews Linx
Target hostname: dns.google
Total hops: 12

 1. gw.example.com (10.0.0.1) 1.2 1.1 1.3 ms
 2. isp-gateway.net (203.0.113.1) [AS 64500] 5.2 5.1 5.3 ms
 3. * (no response)
 4. core-router.example.net (203.0.114.1) [AS 65001] 10.5 10.2 10.8 ms
 ...
12. dns.google (8.8.8.8) [AS 15169] 25.3 25.1 25.5 ms
```

**JSON Output Example:**

```json
{
  "type": "traceroute",
  "ip": "8.8.8.8",
  "target_hostname": "dns.google",
  "server": "RouteViews Linx",
  "total_hops": 12,
  "hops": [
    {
      "hop_number": 1,
      "host": "gw.example.com",
      "ip": "10.0.0.1",
      "asn": null,
      "times_ms": [1.2, 1.1, 1.3],
      "rtt_avg_ms": 1.2
    },
    {
      "hop_number": 2,
      "host": "isp-gateway.net",
      "ip": "203.0.113.1",
      "asn": 64500,
      "times_ms": [5.2, 5.1, 5.3],
      "rtt_avg_ms": 5.2
    },
    {
      "hop_number": 3,
      "host": "*",
      "ip": null,
      "asn": null,
      "times_ms": [],
      "rtt_avg_ms": null
    }
  ],
  "raw_output": "..."
}
```

**Supported Servers:**

- RouteViews Main ✅
- RouteViews Linx ❌ (command not available)
- RouteViews 2 ❌ (command not available)
- Other servers ❌ (limited access)

**Understanding Traceroute Output:**

- **Hops with times** - Successfully responded with latency data
- **Hops with \*** - The router didn't respond to traceroute probes (sometimes routers block ICMP/UDP)
- **AS numbers** - Show which Autonomous Systems (networks) are involved in the path
- **Increasing latency** - Each hop should have higher latency as you get further from the source

**Use cases:**

- Identify the network path between two points on the internet
- Diagnose where network problems occur (which hop fails)
- Understand which ASes are involved in routing traffic
- Verify direct peering relationships between networks
- Map network topology and interconnections
- Debug latency issues by identifying slow hops

---

## Supported Route Servers

7 globally-distributed public RouteViews servers, all freely accessible:

| Server | Location | Response Time | Coverage |
| -------- | ---------- | --------------- | ---------- |
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

The server supports two transport modes:

- **Stdio** (`--stdio`) - For local MCP clients like Claude Desktop
- **Streamable-HTTP** (default) - For web-based MCP clients and remote access

## How It Works

1. **You ask Claude a BGP question** - "What's the AS path to 1.1.1.1?"
2. **Claude calls the appropriate MCP tool** - `route_lookup` with your query
3. **The tool connects to a public route server** via telnet
4. **Executes the BGP command** - `show ip bgp <destination>`
5. **Returns the raw router output** to Claude
6. **Claude interprets and summarizes** the results for you

All communication uses simple on-demand telnet connections - no persistent sessions, no complex infrastructure.

## Project Structure

The server consists of:

- **server.py** - Main MCP server with all tools
- **bgp_lg.py** - Library with worker functions (telnet client, IP validation, ASN lookup, config management)
- **config.json** - Configuration for available route servers
- **pyproject.toml** - Python dependencies

## Examples

### Check if a subnet is routed

```text
User: Is 203.0.113.0/24 currently routed to the internet?
Claude: route_lookup(destination="203.0.113.0/24")
Result: [Shows all routes matching that prefix from the route server]
Claude: Based on the BGP data, this subnet is being announced by AS65001 with these paths...
```

### Look up an ASN owner

```text
User: Who operates AS15169?
Claude: asn_owner(asn="AS15169")
Result: Google LLC
Claude: AS15169 is operated by Google LLC, which owns several large networks...
```

### Compare routing across regions

```text
User: How does traffic to Google DNS (8.8.8.8) route from different regions?
Claude: Calls route_lookup for 8.8.8.8 with different servers
Claude: Shows how different route servers see the path to Google's infrastructure
```

### Monitor route server health

```text
User: Is the Linx route server operating normally?
Claude: bgp_summary(server="RouteViews Linx")
Result: Shows 63 active BGP neighbors, millions of routes, healthy sessions
Claude: Yes, the Linx route server is operating normally with X neighbors...
```

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt` (FastAPI, uvicorn, mcp)

## Installation

```bash
git clone https://github.com/yourusername/bgp-lg-mcp.git
cd bgp-lg-mcp
pip install -e .
```

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Performance

- **Connection time**: 50ms - 1.1s (depending on server)
- **Command execution**: Typically <500ms
- **Total query time**: 0.5s - 1.5s per query
- **No startup delay** - tools available immediately

## Troubleshooting

### Connection Error in Claude Desktop

**Error:** "Connection Error - Check if your MCP server is running..."

**Solution:** Ensure the server is running:

```bash
python3 server.py --stdio
```

And verify the config path in `claude_desktop_config.json` is correct.

### Route lookup returns no results

**Possible causes:**

- The destination is a private IP (10.x.x.x, 192.168.x.x, etc.) - these are blocked for safety
- The route server is temporarily unreachable
- The server is overloaded (try a different server)

**Solution:** Try a different server or verify the IP is public:

```python
route_lookup(destination="1.1.1.1", server="RouteViews Equinix")
```

### Server won't start

**Check:**

- Python 3.7+ is installed: `python3 --version`
- Dependencies are installed: `pip install -e .`
- Port 8000 isn't in use (for streamable-http mode): `lsof -i :8000`

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

## About BGP and Looking Glasses

**BGP (Border Gateway Protocol)** is the routing protocol of the internet. It allows autonomous systems (networks) to exchange routing information.

**A Looking Glass** is a service that exposes a BGP speaker's routing table and allows queries. They're invaluable for:

- Troubleshooting routing issues
- Verifying prefix announcements
- Monitoring BGP session health
- Network operations and visibility

Learn more:

- [Route Views Project](http://www.routeviews.org/) - Maintains the public servers used here
- [BGP Basics](https://en.wikipedia.org/wiki/Border_Gateway_Protocol)
- [Looking Glass Servers](http://www.routeviews.org/routeviews/index.php?type=lg)

## Support

If you encounter issues or have suggestions, please open an issue on GitHub or check the troubleshooting section above.
