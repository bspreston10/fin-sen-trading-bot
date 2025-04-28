import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd 
import numpy as np
from live_trading.settings_loader import LOG_FILE_PATH, REFRESH_SECONDS

# Load CSV file into dashboard
df = pd.read_csv(LOG_FILE_PATH, parse_dates=['timestamp'])

# Sidebar settings
st.sidebar.title("Strategy Dashboard")
st.sidebar.write("Gold XAU/USD Strategy (Live Trading)")

# Update Check
st.sidebar.write(f"Last Update: {df['timestamp'].iloc[-1]}")

# Live Equity Line vs Backtest Equity Line
st.title("Live Equity vs Inital Equity")

df['cum_pnl'] = df['live_equity'] - df['equity'].iloc[0]

st.line_chart(df.set_index('timestamp')[['live_equity', 'cum_pnl']], use_container_width=True)
st.write("### Live Equity vs Initial Equity")

# Current Open Positions
st.title("Current Open Positions")

current_position = df.iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Position", current_position['position'])
col2.metric("Entry Price", f"{current_position['entry_price']:.2f}")
col3.metric("Source", current_position['source'])

col4, col5, col6 = st.columns(3)
col4.metric("RSI Size", f"{current_position['rsi_size']:.2f}")
col5.metric("FOMC Size", f"{current_position['fomc_size']:.2f}")
col6.metric("Sentiment", current_position['sentiment'])

# Rolling 20-day Sharpe and Max DD
st.title("Rolling Metrics")

returns = df['live_equity'].pct_change()

# Rolling Sharpe Ratio
rolling_sharpe = returns.rolling(window=20).mean() / returns.rolling(window=20).std()
rolling_sharpe = rolling_sharpe.dropna()

# Rolling Maximum Drawdown
cum_returns = (1 + returns).cumprod()
rolling_max = cum_returns.cummax()
drawdown = cum_returns / rolling_max - 1
max_drawdown = drawdown.min()

col1, col2 = st.columns(2)
col1.metric("Rolling 20-bar Sharpe Ratio", f"{rolling_sharpe.iloc[-1]:.2f}" if not rolling_sharpe.empty else "N/A")
col2.metric("Max Drawdown", f"{max_drawdown:.2%}")

# Trade Log History
with st.expander("Full Trade Log"):
    st.dataframe(df)