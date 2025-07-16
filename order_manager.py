# order_manager.py

import asyncio
import json
import random
import time
import redis
from config import TRADING_COIN, REDIS_HOST, REDIS_PORT, ORDER_SIZE
from position_manager import get_net_delta, update_net_delta

# In a real build, replace this with signed order submission via API.
def mock_submit_limit_order(side, price, size):
    print(f"[MOCK] Submitted {side.upper()} order for {size} @ {price}")
    return {"order_id": str(random.randint(10000, 99999)), "price": price, "side": side}

def mock_cancel_order(order_id):
    print(f"[MOCK] Canceled order {order_id}")

# Connect to Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

async def market_maker_loop():
    current_order = None
    order_time = None
    side = "buy"  # "buy" or "sell" – you can flip it for one-sided quoting

    while True:
        try:
            orderbook_json = r.get(f"{TRADING_COIN}_orderbook")
            if not orderbook_json:
                await asyncio.sleep(0.1)
                continue

            orderbook = json.loads(orderbook_json)

            # Extract best bid/ask
            best_bid = float(orderbook['bids'][0]['px'])
            best_ask = float(orderbook['asks'][0]['px'])

            # Quote mid minus or plus spread
            spread_buffer = 0.2  # $0.20 offset
            if side == "buy":
                price = best_bid - spread_buffer
            else:
                price = best_ask + spread_buffer

            # Check delta exposure
            delta = get_net_delta()
            if side == "buy" and delta >= ORDER_SIZE:
                print("🛑 Delta too long, skipping buy")
                await asyncio.sleep(1)
                continue
            elif side == "sell" and delta <= -ORDER_SIZE:
                print("🛑 Delta too short, skipping sell")
                await asyncio.sleep(1)
                continue

            # Cancel previous if it's stale
            if current_order and (time.time() - order_time > 5):
                mock_cancel_order(current_order["order_id"])
                current_order = None

            # Place new order if none active
            if not current_order:
                order = mock_submit_limit_order(side, price, ORDER_SIZE)
                current_order = order
                order_time = time.time()

                # Update mock delta
                if side == "buy":
                    update_net_delta(ORDER_SIZE)
                else:
                    update_net_delta(-ORDER_SIZE)

            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[ERROR] in order manager: {e}")
            await asyncio.sleep(1)

