import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from core_types import (
    SignalType, ConfidenceLevel,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    EMA_SHORT, EMA_LONG
)
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators = {}
        
    def analyze(self, df: pd.DataFrame) -> tuple[SignalType, ConfidenceLevel]:
        """Analyze price data and return trading signal with confidence."""
        try:
            # Calculate indicators
            self._calculate_indicators(df)
            
            # Get latest values
            rsi = self.indicators['rsi'].iloc[-1]
            macd = self.indicators['macd'].iloc[-1]
            macd_signal = self.indicators['macd_signal'].iloc[-1]
            ema_short = self.indicators['ema_short'].iloc[-1]
            ema_long = self.indicators['ema_long'].iloc[-1]
            
            # Log indicator values
            logger.info(f"RSI: {rsi:.2f}")
            logger.info(f"MACD: {macd:.2f}")
            logger.info(f"MACD Signal: {macd_signal:.2f}")
            logger.info(f"EMA Short: {ema_short:.2f}")
            logger.info(f"EMA Long: {ema_long:.2f}")
            
            # Count bullish and bearish signals
            bullish_signals = 0
            bearish_signals = 0
            
            # RSI Analysis
            if rsi < RSI_OVERSOLD:
                bullish_signals += 1
            elif rsi > RSI_OVERBOUGHT:
                bearish_signals += 1
                
            # MACD Analysis
            if macd > macd_signal:
                bullish_signals += 1
            elif macd < macd_signal:
                bearish_signals += 1
                
            # EMA Analysis
            if ema_short > ema_long:
                bullish_signals += 1
            elif ema_short < ema_long:
                bearish_signals += 1
            
            # Determine final signal
            if bullish_signals >= 2:
                return SignalType.BUY, ConfidenceLevel.HIGH
            elif bearish_signals >= 2:
                return SignalType.SELL, ConfidenceLevel.HIGH
            elif bullish_signals == 1:
                return SignalType.BUY, ConfidenceLevel.MEDIUM
            elif bearish_signals == 1:
                return SignalType.SELL, ConfidenceLevel.MEDIUM
            else:
                return SignalType.HOLD, ConfidenceLevel.NONE
                
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return SignalType.HOLD, ConfidenceLevel.NONE
            
    def _calculate_indicators(self, df: pd.DataFrame) -> None:
        """Calculate technical indicators."""
        try:
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
            
            # EMA
            ema_short = EMAIndicator(close=df['close'], window=EMA_SHORT)
            ema_long = EMAIndicator(close=df['close'], window=EMA_LONG)
            self.indicators['ema_short'] = ema_short.ema_indicator()
            self.indicators['ema_long'] = ema_long.ema_indicator()
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise 