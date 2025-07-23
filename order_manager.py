# order_manager.py
import os, json, asyncio, time, redis
from collections import deque
from web3 import Web3
from eth_account import Account

from config import (
    TRADING_COIN, REDIS_HOST, REDIS_PORT,
    ORDER_SIZE_USD, MIN_ORDER_SIZE_USD,
    TICK_SIZE, QUOTE_OFFSET_TICKS,
    BASE_MAKER_FEE_PCT, REBATE_PCT,
    VOLATILITY_THRESHOLD_PCT,
    MAX_DELTA_USD,
    API_URL, EXCHANGE_HTTP_URL,
    STALE_TIMEOUT, LOOP_SLEEP, BACKTEST_MODE
)
from position_manager import get_net_delta, update_net_delta
from db import record_fill
from metrics import rebate_total, delta_exposure, realized_pnl
from hyperliquid.exchange import Exchange

#─── backward‐compat shim ─────────────────────────────────────────────────────────
_last_order_id = None
def get_current_order_id():
    return _last_order_id

async def cancel_order(oid: int):
    """
    Cancel a resting order.
    """
    if BACKTEST_MODE:
        print(f"[DRY RUN] Cancel {oid}")
        return

    try:
        hl.cancel(TRADING_COIN, oid)
    except Exception as e:
        print(f"[OM ERROR] cancel_order: {e}")

async def submit_market_order(side: str, size: float) -> int:
    """
    Immediate IOC market fill for flatten/emergency.
    """
    is_buy = side.lower() == "buy"
    dec    = hl.info.asset_to_sz_decimals[asset_id]
    size   = round(size, dec)
    px     = hl._slippage_price(TRADING_COIN, is_buy, slippage=0.0, px=0.0)

    print(f"🚀 MARKET {side.upper():4} {size} @ market")
    fee = px * size * (BASE_MAKER_FEE_PCT - REBATE_PCT)

    record_fill(side, px, size, fee)
    rebate_total.inc(abs(size * px * REBATE_PCT))
    pnl = px * size * (1 if side == "sell" else -1)
    (realized_pnl.inc if pnl >= 0 else realized_pnl.dec)(abs(pnl))
    update_net_delta(-size if side == "sell" else size)
    return 0


#─── setup ───────────────────────────────────────────────────────────────────────
_here = os.path.dirname(__file__)
with open(os.path.join(_here, "examples", "config.json")) as f:
    sdk_cfg = json.load(f)
raw_wallet = Account.from_key(sdk_cfg["secret_key"])
MAIN_ADDR  = Web3.to_checksum_address(sdk_cfg["account_address"])

hl = Exchange(
    wallet=raw_wallet,
    base_url=EXCHANGE_HTTP_URL,
    account_address=MAIN_ADDR,
)
asset_id   = hl.info.name_to_asset(TRADING_COIN)
r          = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# mid‐price history for optional volatility gating
mid_prices = deque(maxlen=5)

#─── helpers ────────────────────────────────────────────────────────────────────
def parse_orderbook(raw):
    if isinstance(raw, bytes):
        raw = raw.decode()
    ob = json.loads(raw) if isinstance(raw, str) else raw
    bids, asks = ob["bids"], ob["asks"]
    return float(bids[0]["px"]), float(asks[0]["px"])

def compute_size_usd():
    delta = abs(get_net_delta())
    cap   = ORDER_SIZE_USD - delta
    if cap <= 0:
        return 0.0
    if cap >= ORDER_SIZE_USD * 0.9:
        return ORDER_SIZE_USD
    return max(MIN_ORDER_SIZE_USD, cap)

def compute_price(side, bid, ask):
    # dynamic spread: widen if vol ↑
    mid = (bid+ask)/2
    mid_prices.append(mid)
    if len(mid_prices)==mid_prices.maxlen:
        vol = (max(mid_prices)-min(mid_prices))/mid
    else:
        vol = 0.0
    # offset ticks scales linearly with vol
    ticks = max(1, int(QUOTE_OFFSET_TICKS*(1 + vol/VOLATILITY_THRESHOLD_PCT)))
    if side=="buy":
        return bid - ticks * TICK_SIZE
    else:
        return ask + ticks * TICK_SIZE

async def submit_limit(side, price, size):
    global _last_order_id
    is_buy = side=="buy"
    dec    = hl.info.asset_to_sz_decimals[asset_id]
    size   = round(size, dec)
    px     = hl._slippage_price(TRADING_COIN, is_buy, slippage=0.0, px=price)

    if BACKTEST_MODE:
        print(f"[DRY] {side} {size}@{px}")
        return int(time.time()*1000)

    resp = hl.order(
        TRADING_COIN, is_buy, size, px,
        order_type={"limit":{"tif":"Alo"}},  # post‐only
        reduce_only=False,
    )
    statuses = resp["response"]["data"]["statuses"]

    # resting
    for s in statuses:
        if "resting" in s:
            oid = s["resting"]["oid"]
            _last_order_id = oid
            return oid

    # fill
    for s in statuses:
        if "filled" in s:
            f=s["filled"]
            sz, avg = float(f["totalSz"]), float(f["avgPx"])
            fee = avg*sz*(BASE_MAKER_FEE_PCT-REBATE_PCT)
            record_fill(side, avg, sz, fee)
            rebate_total.inc(abs(sz*avg*REBATE_PCT))
            pnl = avg*sz*(1 if side=="sell" else -1)
            (realized_pnl.inc if pnl>=0 else realized_pnl.dec)(abs(pnl))
            update_net_delta(sz if side=="buy" else -sz)
            return -1

    return 0

async def cancel(oid):
    if BACKTEST_MODE:
        print(f"[DRY] cancel {oid}")
        return
    try:
        hl.cancel(TRADING_COIN, oid)
    except Exception as e:
        print("cancel error", e)

async def submit_market(side, size):
    # for auto‐flatten
    is_buy = side=="buy"
    dec    = hl.info.asset_to_sz_decimals[asset_id]
    size   = round(size, dec)
    px     = hl._slippage_price(TRADING_COIN, is_buy, slippage=0.0, px=0.0)
    print(f"🚀 MARKET {side} {size}")
    fee = px*size*(BASE_MAKER_FEE_PCT-REBATE_PCT)
    record_fill(side, px, size, fee)
    rebate_total.inc(abs(size*px*REBATE_PCT))
    pnl = px*size*(1 if side=="sell" else -1)
    (realized_pnl.inc if pnl>=0 else realized_pnl.dec)(abs(pnl))
    update_net_delta(-size if side=="sell" else size)
    return 0

#─── main loop ─────────────────────────────────────────────────────────────────
async def market_maker_loop():
    side = "buy"
    current_oid = None
    ts = 0.0

    while True:
        raw = r.get(f"{TRADING_COIN}_orderbook")
        if not raw:
            await asyncio.sleep(LOOP_SLEEP); continue

        bid, ask = parse_orderbook(raw)

        # 1) Risk & auto‐flatten
        delta = get_net_delta(); delta_exposure.set(delta)
        if abs(delta)>=MAX_DELTA_USD*0.95:
            flat = "sell" if delta>0 else "buy"
            amt  = abs(delta)/((bid+ask)/2)
            await submit_market(flat, amt)
            current_oid = None
            ts = 0
            await asyncio.sleep(LOOP_SLEEP); continue

        # 2) Cancel stale
        if current_oid and (time.time()-ts)>STALE_TIMEOUT:
            await cancel(current_oid)
            current_oid = None

        # 3) Place new if none
        if not current_oid:
            size = compute_size_usd()
            if size>=MIN_ORDER_SIZE_USD:
                price = compute_price(side, bid, ask)
                oid   = await submit_limit(side, price, size)
                if oid>0:
                    current_oid = oid
                    ts = time.time()
                elif oid==-1:
                    # immediate fill → flip
                    side = "sell" if side=="buy" else "buy"
                    current_oid = None
                    mid_prices.clear()

        # 4) Check fills
        if current_oid:
            fills = hl.info.user_fills(MAIN_ADDR)
            for f in fills:
                if f.get("oid")==current_oid:
                    side = "sell" if side=="buy" else "buy"
                    current_oid = None
                    mid_prices.clear()
                    break

        await asyncio.sleep(LOOP_SLEEP)

if __name__=="__main__":
    asyncio.run(market_maker_loop())
