# order_manager.py

import asyncio
import json
import random
import time
import redis

from config import (
    TRADING_COIN,
    REDIS_HOST,
    REDIS_PORT,
    ORDER_SIZE,
    SPREAD_BUFFER,
    REBATE_PCT,
)
from position_manager import get_net_delta, update_net_delta
from db import record_fill
from metrics import rebate_total, delta_exposure, realized_pnl

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def mock_submit_limit_order(side, price, size):
    # simulate a fill immediately for testing
    fill_sz = size
    fill_px = price

    # 1) Record the fill in the database (fee is negative rebate)
    fee = -fill_px * fill_sz * REBATE_PCT
    record_fill(side, fill_px, fill_sz, fee)

    # 2) Update rebate counter (always positive)
    rebate_total.inc(fill_px * fill_sz * REBATE_PCT)

    # 3) Compute realized PnL: +px*sz on sell, –px*sz on buy
    pnl = fill_px * fill_sz * (1 if side == "sell" else -1)
    if pnl >= 0:
        realized_pnl.inc(pnl)
    else:
        realized_pnl.dec(-pnl)

    print(f"[MOCK FILL] {side.upper()} {fill_sz}@{fill_px}, pnl=${pnl:.2f}")
    return {"order_id": str(random.randint(10000, 99999))}

def mock_cancel_order(oid):
    print(f"[MOCK] Canceled order {oid}")

async def market_maker_loop():
    side = "buy"
    current_order = None
    order_time = 0

    while True:
        try:
            raw = r.get(f"{TRADING_COIN}_orderbook")
            if not raw:
                await asyncio.sleep(0.1)
                continue

            ob = json.loads(raw)
            best_bid = float(ob['bids'][0]['px'])
            best_ask = float(ob['asks'][0]['px'])
            price = (best_bid - SPREAD_BUFFER) if side == "buy" else (best_ask + SPREAD_BUFFER)

            # Update net delta gauge
            delta = get_net_delta()
            delta_exposure.set(delta)

            # Risk checks
            if side == "buy" and delta >= ORDER_SIZE:
                print("🛑 too long → skip buy")
                await asyncio.sleep(1)
                continue
            if side == "sell" and delta <= -ORDER_SIZE:
                print("🛑 too short → skip sell")
                await asyncio.sleep(1)
                continue

            # Cancel stale order
            if current_order and (time.time() - order_time > 5):
                mock_cancel_order(current_order["order_id"])
                current_order = None

            # Place new order
            if not current_order:
                current_order = mock_submit_limit_order(side, price, ORDER_SIZE)
                order_time = time.time()
                # Adjust our mock position
                update_net_delta(ORDER_SIZE if side == "buy" else -ORDER_SIZE)
                # Flip side for alternating buys/sells
                side = "sell" if side == "buy" else "buy"

            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[OM ERROR] {e}")
            await asyncio.sleep(1)
