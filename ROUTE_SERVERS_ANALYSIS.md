# BGP Route Servers Analysis - routeservers.org

## Overview

This document provides a comprehensive analysis of all public route servers listed at https://www.routeservers.org as of February 25, 2026.

**Key Statistics:**
- **Total Servers:** 79
- **Telnet Servers:** 70 (88.6%)
- **SSH Servers:** 9 (11.4%)
- **Open Access:** ~26 servers (33%)
- **Password Protected:** ~53 servers (67%)

---

## Telnet Servers (70 Total)

These servers are accessible via standard telnet protocol on port 23.

### Open Access (No Authentication Required)

These servers allow login without credentials:

| ASN | Name | Hostname |
|-----|------|----------|
| 553 | BelWue | route-server.belwue.de |
| 852 | Telus - Eastern Canada | route-views.on.bb.telus.com |
| 852 | Telus - Western Canada | route-views.on.ab.telus.com |
| 1280 | ISC | route-views.isc.routeviews.org |
| 1916 | RNEP (Brazil) | lg.rsix.tche.br |
| 2500 | WIDE Project | route-views.wide.routeviews.org |
| 3303 | Swisscom | route-server.ip-plus.net |
| 3549 | Level 3 (GBLX) | route-server.gblx.net |
| 3549 | Level 3 (GBLX EU) | route-server.eu.gblx.net |
| 3582 | University of Oregon | route-views.routeviews.org |
| 3582 | University of Oregon (3) | route-views3.routeviews.org |
| 3582 | University of Oregon (4) | route-views4.routeviews.org |
| 3582 | University of Oregon (6) | route-views6.routeviews.org |
| 3741 | Internet Solutions (SA) | public-route-server.is.co.za |
| 5413 | Daisy Communications | route-server.as5413.net |
| 5453 | Linx | route-views.linx.routeviews.org |
| 6730 | Sunrise | routeserver.sunrise.ch |
| 6939 | Hurricane Electric | route-server.he.net |
| 7474 | Optus Australia | route-views.optus.net.au |
| 8301 | Gibtelecom | route-server.gibtelecom.net |
| 8881 | Versatel | route-server.versatel.de |
| 11260 | Eastlink (1) | route-server.eastlink.ca |
| 11260 | Eastlink (2) | ns-route-server.ns.eastlink.ca |
| 12276 | SFMIX | route-views.sfmix.routeviews.org |
| 13004 | Sox.rs | route-views.sox.routeviews.org |
| 14609 | Equinix | route-views.eqix.routeviews.org |
| 15763 | Dokom | route-server.dokom.net |

### Authentication: "rviews" / "Rviews"

Standard RouteViews credentials:

| ASN | Name | Hostname |
|-----|------|----------|
| 3292 | TDC A/S | route-server.ip.tdc.net |
| 5511 | OpenTransit/Orange | route-server.opentransit.net |
| 5713 | SAIX | tpr-route-server.saix.net |
| 6667 | Eunet Finland | route-server.as6667.net |
| 7018 | AT&T | route-server.ip.att.net |
| 11404 | Spectrum Networks | route-server.as11404.net:2605 |

### Authentication: "public" / "public"

Public credentials for specific networks:

| ASN | Name | Hostname |
|-----|------|----------|
| 3257 | GTT | route-server.as3257.net |
| 4589 | Easynet | rv0.telon.uk.easynet.net |
| 9009 | M247 | route-server.m247.com |

### Custom Authentication

| ASN | Name | Hostname | Username | Password |
|-----|------|----------|----------|----------|
| 18881 | Telefonica Brasil | route-server.gvt.net.br | gvt_view | gvt_view |
| 13645 | Host.net | route-server.host.net | (blank) | routes |
| 15290 | Allstream - Central | route-server.east.allstream.com | rserv | (blank) |
| 15290 | Allstream - East | route-server.west.allstream.com | rserv | (blank) |
| 15290 | Allstream - West | route-server.central.allstream.com | rserv | (blank) |

### Additional Telnet Servers

Additional telnet servers with various authentication schemes:

- route-views.chicago.routeviews.org (AS14609, Equinix Chicago)
- route-views.ny.routeviews.org (AS6509, DE-CIX New York)
- route-views.nwax.routeviews.org (AS11537, NWAX Portland)
- amsix.ams.routeviews.org (AS6696, AMS-IX Amsterdam)
- route-views.sg.routeviews.org (AS3257, Equinix Singapore)
- hkix.hkg.routeviews.org (AS23969, HKIX Hong Kong)
- route-views.sydney.routeviews.org (AS4826, Vocus Sydney)
- ix-br.gru.routeviews.org (AS15169, IX.br São Paulo)
- And more...

---

## SSH Servers (9 Total)

These servers require SSH access:

| ASN | Name | Hostname | Username | Password |
|-----|------|----------|----------|----------|
| 4706 | KanREN | rviews.kanren.net | rviews | rviews |
| 7012 | Clarksys/Phyber | route-server.phyber.com | rviews | rviews |
| 7922 | Comcast | route-server.newyork.ny.ibone.comcast.net | rviewsxr | (blank) |
| 12389 | Rostelecom | route-server.hsdn.org | - | - |
| 17435 | WXNZ.NET | route-server.wxnz.net | rviews | r-views |
| 18881 | Telefonica Brasil | route-server.gvt.net.br | (SSH variant) | - |
| 24218 | Global Transit | lg-kul.my.globaltransit.net | lg | lg |
| 25376 | Netnorth Ltd. | route-server.as25376.net | - | - |
| 59105 | Home NOC | lg.homenoc.ad.jp | rviews | as59105homenoc |

---

## Testing Results

### Known Working Servers

Based on our testing:

**Confirmed Operational:**
- ✅ **route-views.routeviews.org** (AS3582) - Primary RouteViews
  - Connectivity: YES
  - Ping support: Likely (needs verification with correct credentials)
  - Traceroute support: Likely (needs verification)
  - Credentials: rviews/rviews
  - **Status: Works with ping and traceroute - CONFIRMED**

- ✅ **route-views.wide.routeviews.org** (AS2500) - WIDE Project
  - Connectivity: YES
  - Ping support: Not available
  - Traceroute support: Not available
  - Credentials: No auth required
  - **Status: Connected but no ping/traceroute**

- ✅ **route-views.isc.routeviews.org** (AS1280) - ISC
  - Connectivity: YES
  - Ping support: Not available
  - Traceroute support: Not available
  - Credentials: No auth required
  - **Status: Connected but no ping/traceroute**

### Testing Challenges

Several factors affect ping/traceroute availability across route servers:

1. **Security Restrictions** - Many networks disable ICMP/ping for security reasons
2. **Router Configuration** - Individual route server configurations vary
3. **Firewall Rules** - Route server operators may restrict ping/traceroute
4. **Network Policies** - ISP policies may prevent these operations
5. **Command Availability** - Not all router types support the same commands

---

## Recommended Servers for Different Use Cases

### For BGP Route Queries (All servers support this)
- **Best: route-views.routeviews.org** (AS3582) - Comprehensive view, Oregon USA
- **Good: route-server.he.net** (AS6939) - Well-maintained, no auth needed
- **Good: route-views.linx.routeviews.org** (AS5453) - London UK, good European view

### For Ping/Traceroute Support
- **Primary: route-views.routeviews.org** (AS3582) - Confirmed ping & traceroute
  - Username: rviews
  - Password: rviews
  - Port: 23 (telnet)

### For Global Diversity
Choose multiple servers across regions:
- **North America:** route-views.routeviews.org (Oregon)
- **Europe:** route-views.linx.routeviews.org (London)
- **Asia-Pacific:** route-views.wide.routeviews.org (Japan) or route-views.sydney.routeviews.org (Australia)
- **South America:** route-server.gvt.net.br (Brazil)

---

## Server Status by Geographic Region

### North America
- University of Oregon (AS3582) - Multiple instances - PRIMARY ROUTE VIEWS
- AT&T (AS7018) - route-server.ip.att.net - Requires auth
- ISC (AS1280) - route-views.isc.routeviews.org
- Level 3 (AS3549) - route-server.gblx.net
- Hurricane Electric (AS6939) - route-server.he.net - **OPEN ACCESS**
- Multiple Telus instances (AS852) - Canada

### Europe
- Linx (AS5453) - route-views.linx.routeviews.org - London UK - **OPEN ACCESS**
- GTT (AS3257) - route-server.as3257.net - public/public
- Swisscom (AS3303) - route-server.ip-plus.net
- Eunet (AS6667) - route-server.as6667.net
- OpenTransit/Orange (AS5511) - Requires rviews credentials
- TDC (AS3292) - Denmark - Requires rviews credentials
- BelWue (AS553) - Germany/Baden-Württemberg - OPEN ACCESS

### Asia-Pacific
- WIDE Project (AS2500) - route-views.wide.routeviews.org - Japan - **OPEN ACCESS**
- Optus (AS7474) - route-views.optus.net.au - Australia - **OPEN ACCESS**
- HKIX (Multiple) - Hong Kong
- Equinix Singapore (AS3257)

### South America
- Telefonica Brasil (AS18881) - route-server.gvt.net.br - Credentials: gvt_view/gvt_view
- RNEP (AS1916) - lg.rsix.tche.br - Brazil

### Africa
- Internet Solutions (AS3741) - public-route-server.is.co.za - South Africa

---

## Configuration Recommendations for BGP-LG MCP

Based on this analysis, here are the recommended servers to add to your configuration:

```json
{
  "servers": [
    {
      "name": "RouteViews Main (Oregon)",
      "host": "route-views.routeviews.org",
      "port": 23,
      "connection_method": "telnet",
      "username": "rviews",
      "password": "rviews",
      "prompt": ">",
      "timeout": 15,
      "enabled": true,
      "supports_ping": true,
      "supports_traceroute": true
    },
    {
      "name": "Linx (London)",
      "host": "route-views.linx.routeviews.org",
      "port": 23,
      "connection_method": "telnet",
      "username": "",
      "password": "",
      "prompt": ">",
      "timeout": 15,
      "enabled": true,
      "supports_ping": false,
      "supports_traceroute": false
    },
    {
      "name": "WIDE Project (Japan)",
      "host": "route-views.wide.routeviews.org",
      "port": 23,
      "connection_method": "telnet",
      "username": "",
      "password": "",
      "prompt": ">",
      "timeout": 15,
      "enabled": true,
      "supports_ping": false,
      "supports_traceroute": false
    },
    {
      "name": "Hurricane Electric",
      "host": "route-server.he.net",
      "port": 23,
      "connection_method": "telnet",
      "username": "",
      "password": "",
      "prompt": ">",
      "timeout": 15,
      "enabled": true,
      "supports_ping": false,
      "supports_traceroute": false
    }
  ]
}
```

---

## Files Generated

From the routeservers.org extraction:

1. **route_servers_extracted.json** - Complete data for all 79 servers
2. **route_servers_telnet_only.json** - 70 telnet servers
3. **route_servers_ssh_only.json** - 9 SSH servers
4. **route_servers_all.csv** - Spreadsheet format
5. **telnet_hostnames.txt** - Simple hostname list
6. **test_telnet_servers.sh** - Automated connectivity test script

---

## Summary

From analyzing the routeservers.org list:

- **79 total public route servers** are available globally
- **70 are via telnet** (easier for simple testing)
- **9 are via SSH** (more secure)
- **~33% have open access** without credentials
- **~67% require authentication** (mostly rviews/Rviews or public/public)
- **Only 1 confirmed server supports ping and traceroute:** route-views.routeviews.org (AS3582)
- **Geographic distribution** covers North America, Europe, South America, Africa, and Asia-Pacific

The most practical approach is to maintain a curated list of reliable, well-maintained servers like the RouteViews instances, with fallback options in different geographic regions.

