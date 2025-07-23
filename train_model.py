import ccxt
import pandas as pd
import pandas_ta as ta
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from joblib import dump
from datetime import datetime

#─── Load OHLCV data ──────────────────────────────────────────
def fetch_ohlcv(symbol="SOL/USDT", timeframe="5m", limit=1000):
    binance = ccxt.binance()
    ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

#─── Add technical indicators ─────────────────────────────────
def add_indicators(df):
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
    return df

#─── Label the data (1 = price goes up next candle) ───────────
def add_labels(df):
    df["future_close"] = df["close"].shift(-1)
    df["label"] = (df["future_close"] > df["close"]).astype(int)
    return df

#─── Main training routine ────────────────────────────────────
def train_model():
    df = fetch_ohlcv()
    df = add_indicators(df)
    df = add_labels(df)
    df.dropna(inplace=True)

    features = ["rsi", "ema", "macd", "macd_signal", "macd_hist",
                "stochrsi", "adx", "willr", "atr", "roc"]
    X = df[features]
    y = df["label"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, shuffle=False
    )

    model = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.7,
        colsample_bytree=0.9,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("📊 Classification Report:")
    print(classification_report(y_test, y_pred))

    dump(model, "model_xgb.joblib")
    print("✅ Model saved to model_xgb.joblib")

if __name__ == "__main__":
    train_model()
