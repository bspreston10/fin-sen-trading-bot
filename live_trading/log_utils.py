import pandas as pd
from settings_loader import LOG_FILE_PATH
import os

def log_to_csv(
    timestamp, signal, source, price, position, entry_price, entry_date,
    rsi_size, fomc_size, sentiment, probability, fed_date, equity, live_equity,
    drawdown, latency_ms, short_vol, long_vol,
    executed_size, order_status, filled, remaining,
    pnl, slippage, trade_type, direction, exit_price, volatility_10d, rsi_14,
    filepath=LOG_FILE_PATH
):
    log_row = {
        'timestamp': timestamp,
        'signal': signal,
        'source': source,
        'price': price,
        'position': position,
        'entry_price': entry_price,
        'entry_date': entry_date,
        'rsi_size': rsi_size,
        'fomc_size': fomc_size,
        'sentiment': sentiment,
        'probability': probability,
        'fed_date': fed_date,
        'equity': equity,
        'live_equity': live_equity,
        'drawdown': drawdown,
        'latency_ms': latency_ms,
        'short_vol': short_vol,
        'long_vol': long_vol,
        'executed_size': executed_size,
        'order_status': order_status,
        'filled': filled,
        'remaining': remaining,
        'pnl': pnl,
        'slippage': slippage,
        'trade_type': trade_type,
        'direction': direction,
        'exit_price': exit_price,
        'volatility_10d': volatility_10d,
        'rsi_14': rsi_14
    }

    df = pd.DataFrame([log_row])

    # Append to CSV (create header if new)
    if not os.path.isfile(filepath):
        df.to_csv(filepath, index=False)
    else:
        df.to_csv(filepath, mode='a', header=False, index=False)