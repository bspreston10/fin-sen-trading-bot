# Finalized Live Trading-Compatible Strategy Script
# Covers FOMC and RSI logic, allocation logic, and compliance with audit metrics

from fedwatch import fedwatch_sentiment as get_fedwatch_sentiment
from risk_engine import RiskEngine
from ib_insync import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from talib import RSI, MACD

# === Connect to IBKR ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# === XAUUSD CMDTY Contract ===
contract = Contract(symbol='XAUUSD', secType='CMDTY', exchange='SMART', currency='USD')
ib.qualifyContracts(contract)

# === Pull Historical Data ===
bars = ib.reqHistoricalData(
    contract,
    endDateTime=datetime.datetime.now(datetime.UTC).strftime('%Y%m%d-%H:%M:%S'),
    durationStr='2 Y',
    barSizeSetting='4 hours',
    whatToShow='MIDPOINT',
    useRTH=False,
    formatDate=1
)
ib.disconnect()

if not bars:
    print("❌ No data returned. Check contract or IBKR settings.")
    exit()

# === Historical Price DataFrame ===
df = util.df(bars)

# === Strategy State ===
state = {
    'position': None,
    'entry_price': None,
    'entry_date': None,
    'source': None,
    'partial_exit_done': False,
}

# === Logs ===
trade_log = []
pnl_log = []
equity = 100_000
risk_engine = RiskEngine(pd.Series([equity]), df['close'])
sentiment, prob, fed_date = get_fedwatch_sentiment()

# === Backtest Loop ===
for i in range(30, len(df)):
    df_window = df.iloc[:i+1]
    now = df_window['date'].iloc[-1].date()
    price = df_window['close'].iloc[-1]

    # === Strategy Logic ===
    rsi_series = RSI(df_window['close'], timeperiod=14)
    rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else None

    macd_line, macd_signal, _ = MACD(df_window['close'])
    macd_val = macd_line.dropna().iloc[-1] if not macd_line.dropna().empty else None
    macd_sig = macd_signal.dropna().iloc[-1] if not macd_signal.dropna().empty else None

    returns = df_window['close'].pct_change()
    short_vol = risk_engine.realized_volatility(returns, 10).iloc[-1]
    long_vol = risk_engine.realized_volatility(returns, 126).iloc[-1]

    atr_series = risk_engine.rolling_atr()
    if atr_series.dropna().empty:
        continue
    current_atr = atr_series.dropna().iloc[-1]
    median_atr = atr_series.dropna().median()

    rsi_weight, fomc_weight = risk_engine.allocate_weights(short_vol, long_vol, sentiment)
    base_position = risk_engine.determine_position_size(current_atr, median_atr, equity)

    # === Entry Signals ===
    signal = 'HOLD'
    source = None

    if sentiment == 'HIKE' and prob >= 70 and (fed_date - now).days <= 2:
        signal, source, size = 'SELL', 'FOMC', base_position * fomc_weight
    elif sentiment == 'CUT' and prob >= 70 and (fed_date - now).days <= 2:
        signal, source, size = 'BUY', 'FOMC', base_position * fomc_weight
    elif prob < 70 or sentiment == 'STAY':
        if rsi and rsi < 35 and state['position'] is None:
            signal, source, size = 'BUY', 'RSI', base_position * rsi_weight
        elif rsi and rsi > 85 and state['position'] is None:
            signal, source, size = 'SELL', 'RSI', base_position * rsi_weight

    # === Execution ===
    if signal == 'BUY':
        state.update(position='long', entry_price=price, entry_date=now, source=source, partial_exit_done=False)
        trade_log.append({'date': now, 'price': price, 'type': 'entry', 'direction': 'long'})
    elif signal == 'SELL':
        state.update(position='short', entry_price=price, entry_date=now, source=source, partial_exit_done=False)
        trade_log.append({'date': now, 'price': price, 'type': 'entry', 'direction': 'short'})

    # === Exit Logic ===
    if state['position'] == 'long':
        entry = state['entry_price']
        if state['source'] == 'RSI':
            if not state['partial_exit_done'] and price >= entry * 1.015 and macd_sig < macd_val:
                trade_log.append({'date': now, 'price': price, 'type': 'partial', 'direction': 'long'})
                state['partial_exit_done'] = True
            elif (now - state['entry_date']).days >= 15:
                signal = 'CLOSE'
        if price >= entry * 1.05 or price <= entry * 0.97:
            signal = 'CLOSE'

    elif state['position'] == 'short':
        entry = state['entry_price']
        if state['source'] == 'RSI':
            if not state['partial_exit_done'] and price <= entry * 0.985 and macd_sig > macd_val:
                trade_log.append({'date': now, 'price': price, 'type': 'partial', 'direction': 'short'})
                state['partial_exit_done'] = True
            elif (now - state['entry_date']).days >= 15:
                signal = 'CLOSE'
        if price <= entry * 0.95 or price >= entry * 1.03:
            signal = 'CLOSE'

    if signal == 'CLOSE':
        pnl = price - state['entry_price'] if state['position'] == 'long' else state['entry_price'] - price
        pnl_log.append({'date': now, 'pnl': pnl, 'direction': state['position']})
        trade_log.append({'date': now, 'price': price, 'type': 'exit', 'direction': state['position']})
        state.update(position=None, entry_price=None, entry_date=None, source=None, partial_exit_done=False)

# === Post-Analysis ===
pnl_df = pd.DataFrame(pnl_log)
if not pnl_df.empty:
    pnl_df['cumulative'] = pnl_df['pnl'].cumsum()
    sharpe = pnl_df['pnl'].mean() / pnl_df['pnl'].std() * np.sqrt(252) if pnl_df['pnl'].std() else 0
    max_dd = (pnl_df['cumulative'].cummax() - pnl_df['cumulative']).max()
    print(f"\n✅ TOTAL PnL: {pnl_df['pnl'].sum():.2f}")
    print(f"📈 Sharpe Ratio: {sharpe:.2f}")
    print(f"🔻 Max Drawdown: {max_dd:.2f}")
    pnl_df[['date', 'pnl', 'direction']].to_string(index=False)
    
    # Plot
    plt.figure(figsize=(12,6))
    plt.plot(pnl_df['date'], pnl_df['cumulative'], label='Equity Curve')
    plt.title('Equity Curve')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print("⚠️ No trades were closed.")
