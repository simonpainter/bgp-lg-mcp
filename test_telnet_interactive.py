#!/usr/bin/env python3
"""Interactive telnet testing script for BGP looking-glass servers."""

import asyncio
import logging
from bgp_client import BGPTelnetClient

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("BGP Looking Glass Telnet Tester")
    print("=" * 50)
    
    host = input("Enter host (route-server.ip.att.net): ").strip() or "route-server.ip.att.net"
    port = int(input("Enter port (23): ").strip() or "23")
    username = input("Enter username (rviews): ").strip() or "rviews"
    password = input("Enter password (rviews): ").strip() or "rviews"
    prompt = input("Enter prompt indicator (route-server#): ").strip() or "route-server#"
    
    print("\n" + "=" * 50)
    print("Connecting...")
    print("=" * 50 + "\n")
    
    try:
        client = BGPTelnetClient(
            host=host,
            port=port,
            username=username,
            password=password,
            prompt=prompt,
            timeout=30
        )
        
        async with client:
            print("\nConnected! Type commands to send (or 'quit' to exit)\n")
            
            while True:
                try:
                    cmd = input(">> ").strip()
                    if cmd.lower() == 'quit':
                        break
                    if not cmd:
                        continue
                    
                    print(f"\nSending: {cmd}")
                    print("-" * 50)
                    response = await client.send_command(cmd)
                    print(response)
                    print("-" * 50 + "\n")
                    
                except Exception as e:
                    print(f"Error executing command: {e}")
                    break
                    
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
