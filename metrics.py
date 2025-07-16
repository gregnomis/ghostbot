# metrics.py
from prometheus_client import start_http_server, Gauge, Counter
from config import PROMETHEUS_PORT

# total rebates collected (USD)
rebate_total = Counter(
    "ghostbot_rebate_usd_total",
    "Total rebates earned in USD"
)

# current position exposure (USD)
delta_exposure = Gauge(
    "ghostbot_delta_exposure_usd",
    "Current unrealized net position in USD"
)

# total realized PnL (USD)
realized_pnl = Gauge(
    "ghostbot_realized_pnl_usd",
    "Cumulative realized PnL in USD"
)

def start_metrics():
    # spin up the HTTP endpoint on PROMETHEUS_PORT
    start_http_server(PROMETHEUS_PORT)
