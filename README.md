# GhostBot

**GhostBot** is a Python-based market-making and trading bot built for the Hyperliquid exchange. It uses live orderbook data, adaptive sizing, and a simple ML filter to automatically place and manage trades on SOL perpetuals, while exporting Prometheus metrics for real-time monitoring.

---

## 🚀 Features

* **Real‑time orderbook listener** on Hyperliquid WebSocket API
* **Adaptive layering**: places multiple bid/ask layers around mid‑price
* **ML‑based signal filter** (optional) to pause trading during adverse conditions
* **Dynamic risk controls**: configurable max delta, order sizing, volatility thresholds
* **Prometheus metrics** for monitoring fills, PnL, order latency, net delta, and more
* **Backtest/dry‑run mode** to simulate performance without live execution

---

## 📦 Prerequisites

* Python 3.10+
* A Hyperliquid account with API access
* Redis server (for orderbook state caching)
* PostgreSQL (optional, for historical PnL/storage)
* (Optional) Prometheus & Grafana for metrics

---

## 🔧 Installation

1. **Clone this repository**

   ```bash
   git clone https://github.com/gregnomis/ghostbot.git
   cd ghostbot
   ```
2. **Create & activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

The bot reads settings from `config.py`. You can either edit that file directly **or** export the corresponding environment variables:

| Setting              | Env Variable               | Default/Example                                |
| -------------------- | -------------------------- | ---------------------------------------------- |
| Trading pair         | `TRADING_COIN`             | `SOL`                                          |
| WebSocket URL        | `API_URL`                  | `wss://api.hyperliquid.xyz/ws`                 |
| HTTP API URL         | `EXCHANGE_HTTP_URL`        | `https://api.hyperliquid.xyz`                  |
| Redis host/port      | `REDIS_HOST`, `REDIS_PORT` | `localhost`, `6379`                            |
| Postgres DSN         | `POSTGRES_DSN`             | `postgresql://user:pass@host:5432/ghostbot_db` |
| Max USD exposure     | `MAX_DELTA_USD`            | `100`                                          |
| Order size (USD)     | `ORDER_SIZE_USD`           | `50`                                           |
| Volatility threshold | `VOLATILITY_THRESHOLD_PCT` | `0.005`                                        |
| Backtest mode        | `BACKTEST_MODE`            | `False`                                        |

You must **never** commit real credentials into Git. Use environment variables or a secrets manager.

---

## ▶️ Running GhostBot

```bash
# Ensure your venv is active
export TRADING_COIN=SOL
export API_URL=wss://api.hyperliquid.xyz/ws
export EXCHANGE_HTTP_URL=https://api.hyperliquid.xyz
export REDIS_HOST=localhost
export REDIS_PORT=6379
export POSTGRES_DSN="postgresql://user:pass@host:5432/ghostbot_db"
# (Other vars...)

# Run the bot
python main.py
```

* **Prometheus** will scrape metrics at `http://localhost:8000/metrics` by default.
* **Backtesting**: set `BACKTEST_MODE=True` to run a dry‑run.

---

## 📊 Metrics Dashboard

You can point Grafana at your Prometheus instance and visualize metrics:

* `ghostbot_net_delta`
* `ghostbot_trade_rate`
* `ghostbot_latency_ms`
* `ghostbot_unfilled_orders`

---

## 🛠️ Development

* Code is organized under:

  * `websocket_handler.py`: live orderbook listener
  * `order_manager.py`: submit/cancel orders
  * `position_manager.py`: track net exposure
  * `metrics.py`: Prometheus instrumentation
  * `hl_ml_bot.py`: ML‑based filter (optional)

* **Add your changes**, then:

  ```bash
  git add .
  git commit -m "feat: your message"
  git push
  ```

---

## 🤝 Contributing

Contributions, bug reports, and PRs are welcome! Please open an issue first to discuss major changes.

---

