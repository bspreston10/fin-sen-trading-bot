from talib import RSI, MACD


# === State Tracking ===
state = {
    'position': None,
    'entry_price': None,
    'entry_date': None,
    'source': None,
    'partial_exit_done': False
}

def combined_rsi_fomc_logic(
    df_window,
    sentiment,
    prob,
    fed_date,
    state,
    position_size_rsi,
    position_size_fomc
):
    now = df_window['date'].iloc[-1].date()
    close = df_window['close'].iloc[-1]

    # === Indicators ===
    rsi_series = RSI(df_window['close'], timeperiod=14)
    macd_line, macd_signal, _ = MACD(df_window['close'])

    if rsi_series.dropna().empty or macd_line.dropna().empty or macd_signal.dropna().empty:
        return {'signal': 'HOLD', 'type': None, 'size': 0}
    print("RSI Series:", rsi_series)
    print("MACD Line:", macd_line)
    print("MACD Signal:", macd_signal)

    rsi = rsi_series.dropna().iloc[-1]
    macd_val = macd_line.dropna().iloc[-1]
    macd_sig = macd_signal.dropna().iloc[-1]

    # === FOMC Logic ===
    if sentiment == 'HIKE' and prob >= 70 and (fed_date - now).days <= 5:
        return {'signal': 'SELL', 'type': 'FOMC', 'size': position_size_fomc}
    elif sentiment == 'CUT' and prob >= 70 and (fed_date - now).days <= 5:
        return {'signal': 'BUY', 'type': 'FOMC', 'size': position_size_fomc}
    elif sentiment == 'STAY' and prob >= 70 and (fed_date - now).days <= 5:
        return {'signal': 'HOLD', 'type': None, 'size': 0}

    # === RSI Entry Logic ===
    if rsi < 35 and state['position'] is None:
        return {'signal': 'BUY', 'type': 'RSI', 'size': position_size_rsi}
    elif rsi > 85 and state['position'] is None:
        return {'signal': 'SELL', 'type': 'RSI', 'size': position_size_rsi}

    entry = state.get('entry_price')
    entry_date = state.get('entry_date')
    source = state.get('source')

    if entry is None or entry_date is None:
        return {'signal': 'HOLD', 'type': None, 'size': 0}

    # === Manage Long ===
    if state['position'] == 'long':
        if source == 'RSI':
            if not state['partial_exit_done'] and close >= entry * 1.015 and macd_sig < macd_val:
                state['partial_exit_done'] = True
                return {'signal': 'PARTIAL SELL', 'type': 'RSI', 'size': position_size_rsi * 0.4}
            if (now - entry_date).days >= 15:
                return {'signal': 'CLOSE', 'type': 'RSI', 'size': position_size_rsi}
        if close >= entry * 1.05 or close <= entry * 0.97:
            return {'signal': 'CLOSE', 'type': source, 'size': position_size_rsi if source == 'RSI' else position_size_fomc}

    # === Manage Short ===
    elif state['position'] == 'short':
        if source == 'RSI':
            if not state['partial_exit_done'] and close <= entry * 0.985 and macd_sig > macd_val:
                state['partial_exit_done'] = True
                return {'signal': 'PARTIAL COVER', 'type': 'RSI', 'size': position_size_rsi * 0.4}
            if (now - entry_date).days >= 15:
                return {'signal': 'CLOSE', 'type': 'RSI', 'size': position_size_rsi}
        if close <= entry * 0.95 or close >= entry * 1.03:
            return {'signal': 'CLOSE', 'type': source, 'size': position_size_rsi if source == 'RSI' else position_size_fomc}

    return {'signal': 'HOLD', 'type': None, 'size': 0}