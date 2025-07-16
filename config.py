# config.py

TRADING_COIN   = "SOL"
API_URL        = "wss://api.hyperliquid.xyz/ws"
REDIS_HOST     = "localhost"
REDIS_PORT     = 6379
MAX_DELTA_USD  = 100          # max net exposure limit
ORDER_SIZE     = 10           # size per limit order in USD
REBATE_PCT     = 0.00003      # estimated rebate rate
PROMETHEUS_PORT= 8000

# ----------------------------
# new constants for v2 bot
SPREAD_BUFFER  = 0.20         # $0.20 away from mid/bid–ask for quoting

POSTGRES_DSN = "postgresql://ghostbot_user:7n8Qnmpr@localhost:5432/ghostbot_db"
