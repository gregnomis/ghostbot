# position_manager.py

_net_delta = 0

def get_net_delta():
    return _net_delta

def update_net_delta(change):
    global _net_delta
    _net_delta += change

