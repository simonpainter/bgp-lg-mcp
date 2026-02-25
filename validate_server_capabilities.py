#!/usr/bin/env python3
"""
Validate which route servers actually support ping and traceroute commands.
This script connects to each server and tests if the commands work.
"""

import asyncio
import json
import sys
from bgp_lg import execute_bgp_command


async def test_server_capabilities(server_name: str) -> dict:
    """Test if a server supports ping and traceroute."""
    
    results = {
        "server": server_name,
        "ping_supported": False,
        "ping_error": None,
        "traceroute_supported": False,
        "traceroute_error": None,
    }
    
    # Test ping capability (ping a common IP like 8.8.8.8)
    print(f"\n  Testing ping on {server_name}...", end=" ", flush=True)
    try:
        ping_output = await execute_bgp_command(server_name, "ping 8.8.8.8")
        if ping_output and "Success rate" in ping_output:
            results["ping_supported"] = True
            print("✓ SUPPORTED")
        else:
            results["ping_supported"] = False
            results["ping_error"] = "No success rate in output"
            print("✗ NOT SUPPORTED")
    except Exception as e:
        results["ping_supported"] = False
        results["ping_error"] = str(e)
        print(f"✗ ERROR: {e}")
    
    # Test traceroute capability (trace to a common IP like 1.1.1.1)
    print(f"  Testing traceroute on {server_name}...", end=" ", flush=True)
    try:
        traceroute_output = await execute_bgp_command(server_name, "traceroute 1.1.1.1")
        if traceroute_output and "Tracing the route" in traceroute_output:
            results["traceroute_supported"] = True
            print("✓ SUPPORTED")
        else:
            results["traceroute_supported"] = False
            results["traceroute_error"] = "No traceroute output"
            print("✗ NOT SUPPORTED")
    except Exception as e:
        results["traceroute_supported"] = False
        results["traceroute_error"] = str(e)
        print(f"✗ ERROR: {e}")
    
    return results


async def main():
    """Test all route servers."""
    # Load config to get server list
    with open("config.json") as f:
        config = json.load(f)
    
    servers = config.get("servers", [])
    all_results = []
    
    print("=" * 80)
    print("BGP Looking Glass - Route Server Capability Validation")
    print("=" * 80)
    print(f"\nTesting {len(servers)} servers for ping and traceroute support...\n")
    
    for server in servers:
        server_name = server.get("name")
        if not server.get("enabled", True):
            print(f"  SKIPPED: {server_name} (disabled)")
            continue
        
        result = await test_server_capabilities(server_name)
        all_results.append(result)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    ping_supported = [r["server"] for r in all_results if r["ping_supported"]]
    traceroute_supported = [r["server"] for r in all_results if r["traceroute_supported"]]
    
    print(f"\n✓ Servers supporting PING ({len(ping_supported)}):")
    for server in ping_supported:
        print(f"  - {server}")
    
    print(f"\n✓ Servers supporting TRACEROUTE ({len(traceroute_supported)}):")
    for server in traceroute_supported:
        print(f"  - {server}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS FOR config.json")
    print("=" * 80)
    print("\nUpdate config.json with the following flags:\n")
    
    for result in all_results:
        print(f"{result['server']}:")
        print(f'  "supports_ping": {str(result["ping_supported"]).lower()},')
        print(f'  "supports_traceroute": {str(result["traceroute_supported"]).lower()}')
        if result.get("ping_error"):
            print(f'  # ping error: {result["ping_error"]}')
        if result.get("traceroute_error"):
            print(f'  # traceroute error: {result["traceroute_error"]}')
        print()


if __name__ == "__main__":
    asyncio.run(main())
