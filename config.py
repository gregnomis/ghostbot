# config.py
import os 

# Trading pair
TRADING_COIN      = "SOL"

# Endpoints
API_URL           = "wss://api.hyperliquid.xyz/ws"
EXCHANGE_HTTP_URL = "https://api.hyperliquid.xyz"

# Redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Prometheus
PROMETHEUS_PORT = 8000

# Sizing & risk
MAX_DELTA_USD       = 100     # absolute USD exposure cap
ORDER_SIZE_USD      = 50      # target USD per layer
MIN_ORDER_SIZE_USD  = 10      # minimum USD per layer

# Orderbook‐imbalance tilt
IMBALANCE_THRESHOLD = 1.2     # lean into >20% depth skew

# Quote & spread
TICK_SIZE           = 0.01    # SOL perpetual tick
QUOTE_OFFSET_TICKS  = 1       # base offset in ticks

# Fees & rebates
BASE_MAKER_FEE_PCT  = 0.00015  # 0.015%
REBATE_PCT          = 0.00003  # 0.003%

# Volatility filter
VOLATILITY_THRESHOLD_PCT = 0.005  # 0.5% mid‐price swing

# Layering settings
NUM_LAYERS    = 3
LAYER_OFFSETS = [1, 2, 3]   # tick multiples per layer

# Timeouts & pacing
STALE_TIMEOUT = 2.5   # seconds to auto‐cancel unmoved layer
LOOP_SLEEP    = 0.05  # main loop interval (50 ms)

# Latency guard
MAX_LATENCY_MS = 200  # ms to HTTP‐ping /info endpoint

# Backtest dry‐run toggle
BACKTEST_MODE = False

# Database
POSTGRES_DSN = os.environ['POSTGRES_DSN']

