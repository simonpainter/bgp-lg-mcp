#!/usr/bin/env python3
"""Quick test of route lookup functionality."""

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

async def test_connection():
    """Test connection to BGP server."""
    print("Testing BGP server connection...")
    print("=" * 60)
    
    client = BGPTelnetClient(
        host="route-server.ip.att.net",
        port=23,
        username="rviews",
        password="rviews",
        prompt=">",
        timeout=20
    )
    
    try:
        await client.connect()
        print("✓ Connected successfully!")
        
        # Test a simple command
        print("\nSending test command: 'show version'")
        print("-" * 60)
        response = await client.send_command("show version")
        print(response[:500])  # Print first 500 chars
        print("-" * 60)
        
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
