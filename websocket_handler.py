import asyncio
import websockets
import json
import redis
from config import TRADING_COIN, REDIS_HOST, REDIS_PORT

API_URL = "wss://api.hyperliquid.xyz/ws"
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

async def listen_orderbook():
    print(f"📡 Connecting to Hyperliquid WebSocket for {TRADING_COIN}")
    async with websockets.connect(API_URL, ping_interval=None) as ws:
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": TRADING_COIN
            }
        }

        await ws.send(json.dumps(subscribe_msg))
        print(f"✅ Subscribed to l2Book for {TRADING_COIN}\n")

        async def send_heartbeat():
            while True:
                try:
                    await ws.send(json.dumps({"method": "ping"}))
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"[Ping ERROR] {e}")
                    break

        asyncio.create_task(send_heartbeat())

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                print("📡 Raw message:", data)
                if data.get("channel") == "l2Book" and data.get("data", {}).get("coin") == TRADING_COIN:
                    bids = data["data"]["levels"][0]
                    asks = data["data"]["levels"][1]
                    if bids and asks:
                        r.set(f"{TRADING_COIN}_orderbook", json.dumps({"bids": bids, "asks": asks}))
                        print(f"📥 Orderbook update — bid: {bids[0]['px']} ask: {asks[0]['px']}")
            except Exception as e:
                print(f"[WebSocket ERROR] {e}")
                await asyncio.sleep(3)

