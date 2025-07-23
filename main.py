# main.py

import asyncio
import signal
from websocket_handler import listen_orderbook
from order_manager import (
    market_maker_loop,
    cancel_order,
    submit_market_order,
    get_current_order_id,
    get_net_delta,
)
from metrics import start_metrics

SHUTDOWN_TIMEOUT = 5 

async def graceful_shutdown():
    print("\n⚠️  Shutdown requested – cleaning up…")

    # 1) Cancel any outstanding limit order
    oid = get_current_order_id()
    if oid is not None:
        print(f"➖ Cancelling open order {oid}")
        try:
            await cancel_order(oid)
        except Exception as e:
            print(f"[Cleanup] cancel_order failed: {e}")

    # 2) Flatten any residual position with a market order
    delta = get_net_delta()
    if delta != 0:
        side = "sell" if delta > 0 else "buy"
        size = abs(delta)
        print(f"➖ Flattening position via market order: {side} {size}")
        try:
            await submit_market_order(side, size)
        except Exception as e:
            print(f"[Cleanup] submit_market_order failed: {e}")

    # 3) Give everything a moment, then stop
    await asyncio.sleep(1)
    print("✅ Cleanup done, exiting.")
    asyncio.get_event_loop().stop()

async def main():
    print("👻 GhostBot starting...")
    start_metrics()
    print("📊 Prometheus metrics server running on port 8000")
    print("🌐 Starting orderbook listener and market maker loop...\n")

    loop = asyncio.get_event_loop()
    # register our shutdown handler
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(graceful_shutdown()))

    await asyncio.gather(
        listen_orderbook(),
        market_maker_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
