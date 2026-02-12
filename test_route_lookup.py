#!/usr/bin/env python3
"""Test route lookup with proper BGP command."""

import asyncio
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bgp_client import BGPTelnetClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_route_lookup():
    """Test route lookup on BGP server."""
    print("Testing BGP route lookup...")
    print("=" * 60)
    
    client = BGPTelnetClient(
        host="route-server.ip.att.net",
        port=23,
        username="rviews",
        password="rviews",
        prompt="rviews@route-server.ip.att.net>",
        timeout=20
    )
    
    try:
        await client.connect()
        print("✓ Connected successfully!")
        
        # Test a route lookup for Google's DNS
        print("\nSending command: 'show route 8.8.8.8'")
        print("-" * 60)
        response = await client.send_command("show route 8.8.8.8")
        print(response)
        print("-" * 60)
        
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_route_lookup())
