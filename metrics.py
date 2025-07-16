# metrics.py

from prometheus_client import start_http_server, Gauge
from config import PROMETHEUS_PORT

rebate_total = Gauge('rebate_total_usd', 'Total rebates earned in USD')
delta_exposure = Gauge('net_delta_usd', 'Current delta exposure')

def start_metrics():
    start_http_server(PROMETHEUS_PORT)

def update_metrics(rebates=0, delta=0):
    rebate_total.inc(rebates)
    delta_exposure.set(delta)

