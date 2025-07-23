# websocket_handler.py

import asyncio
import websockets
import json
import redis
from config import TRADING_COIN, REDIS_HOST, REDIS_PORT, API_URL

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

async def listen_orderbook():
    print(f"📡 Connecting to Hyperliquid WebSocket for {TRADING_COIN} @ {API_URL}")
    async with websockets.connect(API_URL, ping_interval=None) as ws:
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": TRADING_COIN
            }
        }

        await ws.send(json.dumps(subscribe_msg))

        async def send_heartbeat():
            while True:
                try:
                    await ws.send(json.dumps({"method": "ping"}))
                    await asyncio.sleep(10)
                except Exception as e:
                    break

        asyncio.create_task(send_heartbeat())

        try:
            while True:
                msg = await ws.recv()

                try:
                    data = json.loads(msg)
                except Exception as e:
                    continue

                if data.get("channel") == "l2Book" and data["data"].get("coin") == TRADING_COIN:
                    try:
                        bids = data["data"]["levels"][0]
                        asks = data["data"]["levels"][1]

                        if bids and asks:
                            orderbook_data = json.dumps({"bids": bids, "asks": asks})
                            r.set(f"{TRADING_COIN}_orderbook", orderbook_data)

                    except Exception as e:
                        continue

        except Exception as e:
            await asyncio.sleep(3)
