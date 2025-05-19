import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from config import *

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators = {}
        self.signals = {}

    def calculate_indicators(self, df):
        """Calculate all technical indicators for the given price data."""
        # RSI
        rsi = RSIIndicator(close=df['close'], window=RSI_PERIOD)
        self.indicators['rsi'] = rsi.rsi()

        # MACD
        macd = MACD(
            close=df['close'],
            window_slow=MACD_SLOW,
            window_fast=MACD_FAST,
            window_sign=MACD_SIGNAL
        )
        self.indicators['macd'] = macd.macd()
        self.indicators['macd_signal'] = macd.macd_signal()
        self.indicators['macd_diff'] = macd.macd_diff()

        # EMAs
        ema_short = EMAIndicator(close=df['close'], window=EMA_SHORT)
        ema_long = EMAIndicator(close=df['close'], window=EMA_LONG)
        self.indicators['ema_short'] = ema_short.ema_indicator()
        self.indicators['ema_long'] = ema_long.ema_indicator()

        # Bollinger Bands
        bb = BollingerBands(close=df['close'], window=BB_PERIOD, window_dev=BB_STD)
        self.indicators['bb_upper'] = bb.bollinger_hband()
        self.indicators['bb_middle'] = bb.bollinger_mavg()
        self.indicators['bb_lower'] = bb.bollinger_lband()

    def get_rsi_signal(self):
        """Generate RSI-based signal."""
        rsi = self.indicators['rsi'].iloc[-1]
        if rsi < RSI_OVERSOLD:
            return SignalType.BUY
        elif rsi > RSI_OVERBOUGHT:
            return SignalType.SELL
        return SignalType.HOLD

    def get_macd_signal(self):
        """Generate MACD-based signal."""
        macd = self.indicators['macd'].iloc[-1]
        signal = self.indicators['macd_signal'].iloc[-1]
        if macd > signal:
            return SignalType.BUY
        elif macd < signal:
            return SignalType.SELL
        return SignalType.HOLD

    def get_ema_signal(self):
        """Generate EMA crossover signal."""
        ema_short = self.indicators['ema_short'].iloc[-1]
        ema_long = self.indicators['ema_long'].iloc[-1]
        if ema_short > ema_long:
            return SignalType.BUY
        elif ema_short < ema_long:
            return SignalType.SELL
        return SignalType.HOLD

    def get_bb_signal(self, price):
        """Generate Bollinger Bands signal."""
        bb_upper = self.indicators['bb_upper'].iloc[-1]
        bb_lower = self.indicators['bb_lower'].iloc[-1]
        if price < bb_lower:
            return SignalType.BUY
        elif price > bb_upper:
            return SignalType.SELL
        return SignalType.HOLD

    def analyze(self, df):
        """Analyze price data and generate trading signals."""
        self.calculate_indicators(df)
        current_price = df['close'].iloc[-1]

        # Get signals from each indicator
        signals = {
            'rsi': self.get_rsi_signal(),
            'macd': self.get_macd_signal(),
            'ema': self.get_ema_signal(),
            'bb': self.get_bb_signal(current_price)
        }

        # Count bullish and bearish signals
        bullish_count = sum(1 for signal in signals.values() if signal == SignalType.BUY)
        bearish_count = sum(1 for signal in signals.values() if signal == SignalType.SELL)

        # Determine final signal based on confluence
        if bullish_count >= 3:
            return SignalType.BUY, ConfidenceLevel.HIGH
        elif bearish_count >= 3:
            return SignalType.SELL, ConfidenceLevel.HIGH
        elif bullish_count == 2:
            return SignalType.BUY, ConfidenceLevel.MEDIUM
        elif bearish_count == 2:
            return SignalType.SELL, ConfidenceLevel.MEDIUM
        elif bullish_count == 1:
            return SignalType.BUY, ConfidenceLevel.LOW
        elif bearish_count == 1:
            return SignalType.SELL, ConfidenceLevel.LOW
        else:
            return SignalType.HOLD, ConfidenceLevel.NONE 