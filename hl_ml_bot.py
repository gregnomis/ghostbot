# hl_ml_bot.py
import asyncio, json, redis
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from joblib import load
from websocket_handler import listen_orderbook
from datetime import timezone


from config import TRADING_COIN, REDIS_HOST, REDIS_PORT, ORDER_SIZE_USD, MIN_ORDER_SIZE_USD
from order_manager import submit_market_order

#─── ML Setup ──────────────────────────────────────────────
MODEL_PATH   = "model_xgb.joblib" 
MIN_PROB     = 0.6
INTERVAL_MIN = 5
LOOKBACK     = 50  

in_position = False
position_side = None  
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
model = load(MODEL_PATH)
scaler = StandardScaler()

candles = []

#─── OHLC Builder ──────────────────────────────────────────
def add_to_candles(orderbook):
    px = (float(orderbook["bids"][0]["px"]) + float(orderbook["asks"][0]["px"])) / 2
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    now -= timedelta(minutes=now.minute % INTERVAL_MIN)

    if not candles or candles[-1]['time'] != now:
        candles.append({'time': now, 'open': px, 'high': px, 'low': px, 'close': px})
    else:
        candles[-1]['high'] = max(candles[-1]['high'], px)
        candles[-1]['low'] = min(candles[-1]['low'], px)
        candles[-1]['close'] = px

    if len(candles) > LOOKBACK:
        candles.pop(0)



#─── Feature Generator ─────────────────────────────────────
def extract_features(df):
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["ema"] = ta.ema(df["close"], length=14)

    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    df["macd_hist"] = macd["MACDh_12_26_9"]

    df["stochrsi"] = ta.stochrsi(df["close"])["STOCHRSIk_14_14_3_3"]
    df["adx"] = ta.adx(df["high"], df["low"], df["close"])["ADX_14"]
    df["willr"] = ta.willr(df["high"], df["low"], df["close"])
    df["atr"] = ta.atr(df["high"], df["low"], df["close"])
    df["roc"] = ta.roc(df["close"])

    df.dropna(inplace=True)
    return df[["rsi", "ema", "macd", "macd_signal", "macd_hist",
               "stochrsi", "adx", "willr", "atr", "roc"]]


#─── Trading Brain ─────────────────────────────────────────
async def trade_loop():
    print("📊 Indicator-Based Trading Loop Started")
    asyncio.create_task(listen_orderbook())

    dots = ""
    while len(candles) < LOOKBACK:
        raw = r.get(f"{TRADING_COIN}_orderbook")
        if raw:
            ob = json.loads(raw)
            add_to_candles(ob)
        dots += "."
        print(f"⏳ Gathering market data{dots}", end="\r")
        await asyncio.sleep(3)

    print("\n✅ Sufficient candles collected — starting trades!\n")

    global in_position, position_side

    while True:
        raw = r.get(f"{TRADING_COIN}_orderbook")
        if not raw:
            await asyncio.sleep(1)
            continue

        ob = json.loads(raw)
        add_to_candles(ob)

        df = pd.DataFrame(candles)
        indicators = extract_features(df.copy())
        if indicators.empty:
            await asyncio.sleep(3)
            continue

        last = indicators.iloc[-1]
        px = candles[-1]['close']

        # --- BUY CONDITIONS ---
        buy_signal = (
            last["rsi"] < 30 and
            last["macd"] > last["macd_signal"] and
            df["ema"].iloc[-1] > df["ema"].iloc[-2]
        )

        # --- SELL CONDITIONS ---
        sell_signal = (
            last["rsi"] > 70 and
            last["macd"] < last["macd_signal"] and
            df["ema"].iloc[-1] < df["ema"].iloc[-2]
        )

        if buy_signal and not in_position:
            print(f"🟢 BUY @ {px:.2f} | RSI: {last['rsi']:.2f} | MACD Crossover")
            await submit_market_order("buy", ORDER_SIZE_USD / px)
            in_position = True
            position_side = "long"

        elif sell_signal and not in_position:
            print(f"🔴 SELL @ {px:.2f} | RSI: {last['rsi']:.2f} | MACD Crossdown")
            await submit_market_order("sell", ORDER_SIZE_USD / px)
            in_position = True
            position_side = "short"

        # Close position logic
        elif in_position:
            # Close long if RSI is back to neutral
            if position_side == "long" and last["rsi"] > 50:
                print(f"⚪ CLOSE LONG @ {px:.2f} | RSI normalized")
                await submit_market_order("sell", ORDER_SIZE_USD / px)
                in_position = False
                position_side = None

            # Close short if RSI is back to neutral
            elif position_side == "short" and last["rsi"] < 50:
                print(f"⚪ CLOSE SHORT @ {px:.2f} | RSI normalized")
                await submit_market_order("buy", ORDER_SIZE_USD / px)
                in_position = False
                position_side = None

        await asyncio.sleep(5)


#─── Start ─────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(trade_loop())
