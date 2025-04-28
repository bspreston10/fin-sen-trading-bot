from ib_insync import IB, Contract, MarketOrder, util
from fedwatch import fedwatch_sentiment as get_fedwatch_sentiment
from log_utils import log_to_csv
from risk_engine import RiskEngine
from live_strats import combined_rsi_fomc_logic
from alert_utils import send_telegram_alert
import talib
import pandas as pd
import datetime
import time
from settings_loader import (
    HOST, PORT, CLIENT_ID,
    SYMBOL, SEC_TYPE, EXCHANGE, CURRENCY,
    DURATION, BAR_SIZE, DRAW_DOWN_ALERT,
    POLL_INTERVAL
)

# === IBKR Setup ===
ib = IB()
ib.connect(HOST, PORT, clientId=CLIENT_ID)
contract = Contract(symbol=SYMBOL, secType=SEC_TYPE, exchange=EXCHANGE, currency=CURRENCY)
ib.qualifyContracts(contract)
# === Initialize State ===
state = {
    'position': None,
    'entry_price': None,
    'entry_date': None,
    'source': None,
    'partial_exit_done': False
}

account_summary = ib.accountSummary()
account_df = util.df(account_summary)

initial_equity = float(account_df.loc[account_df['tag'] == 'NetLiquidation', 'value'].values[0])

# === Live Loop ===
start_time = time.time()

# Default trade metadata
executed_size = None
order_status = None
filled = None
remaining = None
while True:
    try:
        # === 1. Get Latest Data ===
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=DURATION,
            barSizeSetting=BAR_SIZE,
            whatToShow='MIDPOINT',
            useRTH=False,
            formatDate=1
        )
        df = util.df(bars)
        df_window = df.copy()

        rsi_series = talib.RSI(df_window['close'], timeperiod=14)
        latest_rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else None

        # === 2. Setup Risk Engine ===
        risk_engine = RiskEngine(pd.Series([initial_equity]), df['close'])
        # === 3. Get FedWatch Sentiment ===
        fed_sentiment, fed_prob, fed_date = get_fedwatch_sentiment()
        risk_output = risk_engine.compute_dynamic_size(df_window, fed_sentiment, fed_prob)
        position_size_rsi = risk_output['base_size'].iloc[0] * risk_output['rsi_weight']
        position_size_fomc = risk_output['base_size'].iloc[0] * risk_output['fomc_weight']

        print(f"Position Size RSI: {position_size_rsi:.2f} | Position Size FOMC: {position_size_fomc:.2f}")
        # === 4. Apply Strategy ===
        plan = combined_rsi_fomc_logic(
            df_window,
            fed_sentiment,
            fed_prob,
            fed_date,
            state,
            position_size_rsi,
            position_size_fomc
        )
        print(f"Returned plan: {plan}")
        signal = plan['signal']
        print(f"Signal: {signal}")
        source = plan['type']

        # === 5. Place Order ===
        if signal in ['BUY', 'SELL']:
            size = position_size_rsi if source == 'RSI' else position_size_fomc
            size = round(size, 1)

            order = MarketOrder(signal, size)
            trade = ib.placeOrder(contract, order)
            ib.sleep(1)  # give IBKR time to process order status

            executed_size = trade.orderStatus.filled
            filled = trade.orderStatus.filled
            remaining = trade.orderStatus.remaining
            order_status = trade.orderStatus.status

            print(f"{datetime.datetime.now()} - Placed {signal} order of size {size:.2f} ({source})")
            print(f"📥 Order Status: {order_status} | Filled: {filled} | Remaining: {remaining}")

        elif signal in ['CLOSE', 'PARTIAL_SELL', 'PARTIAL_COVER']:
            print(f"{datetime.datetime.now()} - {signal} triggered")

    except Exception as e:
        print(f"❌ Error: {e}")

    latency_ms = (time.time() - start_time) * 1000

    # Simulate equity change
    current_price = df_window['close'].iloc[-1]
    if state['position'] == 'long':
        live_equity = initial_equity + (current_price - state['entry_price']) * plan['size']
    elif state['position'] == 'short':
        live_equity = initial_equity + (state['entry_price'] - current_price) * plan['size']
    else:
        live_equity = initial_equity

    # Compute drawdown
    equity_peak = max(live_equity, initial_equity)  # for now
    drawdown = live_equity - equity_peak

    # Telegram alert if drawdown exceeds -5%
    if drawdown < -DRAW_DOWN_ALERT * initial_equity:
        send_telegram_alert(f"⚠️ Drawdown Alert!\nLive equity has dropped to {live_equity:.2f} USD\nDD: {drawdown:.2f} USD")

    # === PnL and Trade Metadata ===
    if signal == 'CLOSE':
        direction = state['position']
        entry_price = state['entry_price']
        exit_price = current_price
        trade_type = 'exit'

        if direction == 'long':
            pnl = (exit_price - entry_price) * plan['size']
        elif direction == 'short':
            pnl = (entry_price - exit_price) * plan['size']
        else:
            pnl = 0
    else:
        trade_type = 'entry' if signal in ['BUY', 'SELL'] else 'hold'
        direction = state['position']
        exit_price = None
        pnl = 0

    # Compute 10 day volatility
    returns = df_window['close'].pct_change()
    short_vol_10d = risk_engine.realized_volatility(returns, 10).iloc[-1]

    # === 6. Log Strategy State ===
    print("\n🕒 [LOG UPDATE] Strategy Status:")
    print(f"📅 Current Time: {datetime.datetime.now()}")
    print(f"📊 Signal: {signal}")
    print(f"📈 Price: {df_window['close'].iloc[-1]:.2f}")
    print(f"⚙️ Source: {source}")
    print(f"💰 Position: {state['position']}")
    print(f"🛠 Entry Price: {state['entry_price']}")
    print(f"⏳ Entry Date: {state['entry_date']}")
    print(f"📦 RSI Size: {position_size_rsi:.2f} | FOMC Size: {position_size_fomc:.2f}")
    print(f"🎯 Sentiment: {fed_sentiment} | Prob: {fed_prob:.1f}% | Meeting: {fed_date}")
    print(f"🪙 Equity (simulated): {initial_equity:.2f}")
    print(f"⏱ Latency: {latency_ms:.2f} ms")
    print(f"📊 Short Volatility: {risk_output['short_vol']:.2f}")
    print(f"📊 Long Volatility: {risk_output['long_vol']:.2f}")
    print(f"💵 Live Equity: {live_equity:.2f}")
    print("Volatility (10d):", short_vol_10d)
    print(f"📉 Drawdown: {drawdown:.2f}")
    print(f"📉 RSI (14): {latest_rsi:.2f}" if latest_rsi else "📉 RSI: N/A")
    print("----------------------------------------------------------")

    # === Default values if no trade was placed ===
    executed_size = executed_size if executed_size is not None else 0
    order_status = order_status if order_status is not None else 'None'
    filled = filled if filled is not None else 0
    remaining = remaining if remaining is not None else 0

    try:
        executed_price = trade.orderStatus.avgFillPrice
        slippage = abs(executed_price - df_window['close'].iloc[-1])
    except NameError:
        executed_price = 0
        slippage = 0

    log_to_csv(
        timestamp=datetime.datetime.now().isoformat(),
        signal=signal,
        source=source,
        price=df_window['close'].iloc[-1],
        position=state['position'],
        entry_price=state['entry_price'],
        entry_date=state['entry_date'].isoformat() if state['entry_date'] else None,
        rsi_size=float(position_size_rsi),
        fomc_size=float(position_size_fomc),
        sentiment=fed_sentiment,
        probability=fed_prob,
        fed_date=fed_date.isoformat(),
        equity=initial_equity,
        live_equity=live_equity,
        drawdown=drawdown,
        latency_ms=latency_ms,
        short_vol=risk_output['short_vol'],
        long_vol=risk_output['long_vol'],
        executed_size=executed_size,
        order_status=order_status,
        filled=filled,
        remaining=remaining,
        pnl=pnl,
        slippage=slippage if slippage else 0,
        trade_type=trade_type,
        direction=direction,
        exit_price=exit_price,
        volatility_10d=short_vol_10d,
        rsi_14=latest_rsi
    )
    
    print("✅ Log updated to CSV.")
    print("----------------------------------------------------------")

    time.sleep(POLL_INTERVAL)  # 4-hour polling