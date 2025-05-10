import pandas as pd
import numpy as np

class RiskEngine:
    def __init__(self, equity: float, price_series: pd.Series):
        self.equity = equity
        self.price_series = price_series

    def rolling_atr(self, window: int = 20) -> pd.Series:
        high = self.price_series.rolling(window=2).max()
        low = self.price_series.rolling(window=2).min()
        close = self.price_series

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        return tr.rolling(window=window).mean()

    def realized_volatility(self, returns: pd.Series, window: int) -> pd.Series:
        return returns.rolling(window=window).std() * np.sqrt(252)

    def determine_position_size(self, current_atr: float, median_atr: float, risk_per_trade: float = 0.01) -> float:
        base_size = self.equity * risk_per_trade / current_atr
        if current_atr > 1.3 * median_atr:
            return base_size * 0.5  # scale down FOMC legs
        return base_size

    def allocate_weights(self, short_vol: float, long_vol: float, fedwatch_sentiment: str, fedwatch_prob: float) -> tuple:
        switch = short_vol > 1.5 * long_vol and fedwatch_prob >= 70 and fedwatch_sentiment in ['HIKE', 'CUT']
        if switch:
            return 0.0, 1.5  # 150% FOMC, 0% RSI
        return 0.7, 0.3  # 70% RSI, 30% FOMC

    def compute_dynamic_size(self, df_window: pd.DataFrame, fedwatch_sentiment: str, fedwatch_prob: float) -> dict:
        current_price = df_window['close'].iloc[-1]
        returns = df_window['close'].pct_change()

        # Volatility
        short_vol = self.realized_volatility(returns, 10).iloc[-1]
        long_vol = self.realized_volatility(returns, 126).iloc[-1]

        # ATR
        atr_series = self.rolling_atr(window=20)
        current_atr = atr_series.iloc[-1]
        median_atr = atr_series.median()

        # Position size (1% VaR)
        base_size = self.determine_position_size(current_atr, median_atr)

        # Strategy Weights
        rsi_weight, fomc_weight = self.allocate_weights(short_vol, long_vol, fedwatch_sentiment, fedwatch_prob)

        return {
            'base_size': base_size,
            'rsi_weight': rsi_weight,
            'fomc_weight': fomc_weight,
            'short_vol': short_vol,
            'long_vol': long_vol,
            'current_atr': current_atr,
            'median_atr': median_atr
        }
