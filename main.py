# main.py

import asyncio
from websocket_handler import listen_orderbook
from order_manager import market_maker_loop
from metrics import start_metrics

async def main():
    print("👻 GhostBot starting...")
    start_metrics()
    print("📊 Prometheus metrics server running on port 8000")
    print("🌐 Starting orderbook listener and market maker loop...\n")

    await asyncio.gather(
        listen_orderbook(),
        market_maker_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🧹 GhostBot stopped by user.")

