import pandas as pd
import numpy as np
from typing import Tuple
import logging
from core_types import SignalType, ConfidenceLevel

logger = logging.getLogger(__name__)

class PatternRecognizer:
    def __init__(self):
        self.patterns = {
            'double_top': self._check_double_top,
            'double_bottom': self._check_double_bottom,
            'head_and_shoulders': self._check_head_and_shoulders,
            'inverse_head_and_shoulders': self._check_inverse_head_and_shoulders,
            'bullish_engulfing': self._check_bullish_engulfing,
            'bearish_engulfing': self._check_bearish_engulfing,
            'morning_star': self._check_morning_star,
            'evening_star': self._check_evening_star
        }
        
    def analyze(self, df: pd.DataFrame) -> Tuple[SignalType, ConfidenceLevel]:
        """Analyze price data for chart patterns."""
        try:
            # Calculate additional indicators for pattern recognition
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
            df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
            df['body'] = abs(df['close'] - df['open'])
            
            # Get the last 3 candles for candlestick patterns
            last_3_candles = df.tail(3)
            
            # Check for patterns
            bullish_patterns = []
            bearish_patterns = []
            
            # Check candlestick patterns first (they're more immediate)
            if self._check_bullish_engulfing(last_3_candles):
                bullish_patterns.append(('bullish_engulfing', 0.8))
            if self._check_bearish_engulfing(last_3_candles):
                bearish_patterns.append(('bearish_engulfing', 0.8))
            if self._check_morning_star(last_3_candles):
                bullish_patterns.append(('morning_star', 0.9))
            if self._check_evening_star(last_3_candles):
                bearish_patterns.append(('evening_star', 0.9))
                
            # Check larger patterns
            if self._check_double_bottom(df):
                bullish_patterns.append(('double_bottom', 0.7))
            if self._check_double_top(df):
                bearish_patterns.append(('double_top', 0.7))
            if self._check_head_and_shoulders(df):
                bearish_patterns.append(('head_and_shoulders', 0.8))
            if self._check_inverse_head_and_shoulders(df):
                bullish_patterns.append(('inverse_head_and_shoulders', 0.8))
                
            # Check trend patterns
            if self._check_uptrend(df):
                bullish_patterns.append(('uptrend', 0.6))
            if self._check_downtrend(df):
                bearish_patterns.append(('downtrend', 0.6))
                
            # Log detected patterns
            if bullish_patterns:
                logger.info(f"Detected bullish patterns: {bullish_patterns}")
            if bearish_patterns:
                logger.info(f"Detected bearish patterns: {bearish_patterns}")
                
            # Determine signal based on patterns
            if bullish_patterns and not bearish_patterns:
                return SignalType.BUY, ConfidenceLevel.HIGH
            elif bearish_patterns and not bullish_patterns:
                return SignalType.SELL, ConfidenceLevel.HIGH
            elif bullish_patterns and bearish_patterns:
                # If both patterns exist, use the one with higher confidence
                max_bullish = max(bullish_patterns, key=lambda x: x[1])
                max_bearish = max(bearish_patterns, key=lambda x: x[1])
                if max_bullish[1] > max_bearish[1]:
                    return SignalType.BUY, ConfidenceLevel.MEDIUM
                else:
                    return SignalType.SELL, ConfidenceLevel.MEDIUM
                    
            return SignalType.HOLD, ConfidenceLevel.NONE
            
        except Exception as e:
            logger.error(f"Error in pattern recognition: {e}")
            return SignalType.HOLD, ConfidenceLevel.NONE
            
    def _check_uptrend(self, df: pd.DataFrame) -> bool:
        """Check for uptrend pattern."""
        try:
            # Check if price is above both SMAs and SMAs are aligned
            last_row = df.iloc[-1]
            return (last_row['close'] > last_row['sma_20'] > last_row['sma_50'] and
                   df['sma_20'].iloc[-5:].is_monotonic_increasing)
        except Exception as e:
            logger.error(f"Error checking uptrend: {e}")
            return False
            
    def _check_downtrend(self, df: pd.DataFrame) -> bool:
        """Check for downtrend pattern."""
        try:
            # Check if price is below both SMAs and SMAs are aligned
            last_row = df.iloc[-1]
            return (last_row['close'] < last_row['sma_20'] < last_row['sma_50'] and
                   df['sma_20'].iloc[-5:].is_monotonic_decreasing)
        except Exception as e:
            logger.error(f"Error checking downtrend: {e}")
            return False
            
    def _check_bullish_engulfing(self, candles: pd.DataFrame) -> bool:
        """Check for bullish engulfing pattern."""
        try:
            if len(candles) < 2:
                return False
                
            prev_candle = candles.iloc[-2]
            curr_candle = candles.iloc[-1]
            
            # Check if previous candle is bearish and current is bullish
            is_prev_bearish = prev_candle['close'] < prev_candle['open']
            is_curr_bullish = curr_candle['close'] > curr_candle['open']
            
            # Check if current candle engulfs previous
            is_engulfing = (curr_candle['open'] < prev_candle['close'] and
                          curr_candle['close'] > prev_candle['open'])
            
            return is_prev_bearish and is_curr_bullish and is_engulfing
        except Exception as e:
            logger.error(f"Error checking bullish engulfing: {e}")
            return False
            
    def _check_bearish_engulfing(self, candles: pd.DataFrame) -> bool:
        """Check for bearish engulfing pattern."""
        try:
            if len(candles) < 2:
                return False
                
            prev_candle = candles.iloc[-2]
            curr_candle = candles.iloc[-1]
            
            # Check if previous candle is bullish and current is bearish
            is_prev_bullish = prev_candle['close'] > prev_candle['open']
            is_curr_bearish = curr_candle['close'] < curr_candle['open']
            
            # Check if current candle engulfs previous
            is_engulfing = (curr_candle['open'] > prev_candle['close'] and
                          curr_candle['close'] < prev_candle['open'])
            
            return is_prev_bullish and is_curr_bearish and is_engulfing
        except Exception as e:
            logger.error(f"Error checking bearish engulfing: {e}")
            return False
            
    def _check_morning_star(self, candles: pd.DataFrame) -> bool:
        """Check for morning star pattern."""
        try:
            if len(candles) < 3:
                return False
                
            first = candles.iloc[-3]
            second = candles.iloc[-2]
            third = candles.iloc[-1]
            
            # First candle is bearish
            is_first_bearish = first['close'] < first['open']
            
            # Second candle has small body
            is_second_small = second['body'] < (first['body'] * 0.3)
            
            # Third candle is bullish
            is_third_bullish = third['close'] > third['open']
            
            # Third candle closes above midpoint of first candle
            is_third_strong = third['close'] > (first['open'] + first['close']) / 2
            
            return (is_first_bearish and is_second_small and 
                   is_third_bullish and is_third_strong)
        except Exception as e:
            logger.error(f"Error checking morning star: {e}")
            return False
            
    def _check_evening_star(self, candles: pd.DataFrame) -> bool:
        """Check for evening star pattern."""
        try:
            if len(candles) < 3:
                return False
                
            first = candles.iloc[-3]
            second = candles.iloc[-2]
            third = candles.iloc[-1]
            
            # First candle is bullish
            is_first_bullish = first['close'] > first['open']
            
            # Second candle has small body
            is_second_small = second['body'] < (first['body'] * 0.3)
            
            # Third candle is bearish
            is_third_bearish = third['close'] < third['open']
            
            # Third candle closes below midpoint of first candle
            is_third_strong = third['close'] < (first['open'] + first['close']) / 2
            
            return (is_first_bullish and is_second_small and 
                   is_third_bearish and is_third_strong)
        except Exception as e:
            logger.error(f"Error checking evening star: {e}")
            return False
            
    def _check_double_top(self, df: pd.DataFrame) -> bool:
        """Check for double top pattern."""
        try:
            # Look for two peaks of similar height
            window = 20
            if len(df) < window:
                return False
                
            recent_data = df.tail(window)
            peaks = []
            
            for i in range(1, len(recent_data) - 1):
                if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1]):
                    peaks.append((i, recent_data['high'].iloc[i]))
                    
            if len(peaks) >= 2:
                # Check if the two highest peaks are similar in height
                peaks.sort(key=lambda x: x[1], reverse=True)
                height_diff = abs(peaks[0][1] - peaks[1][1]) / peaks[0][1]
                return height_diff < 0.02  # 2% difference threshold
                
            return False
        except Exception as e:
            logger.error(f"Error checking double top: {e}")
            return False
            
    def _check_double_bottom(self, df: pd.DataFrame) -> bool:
        """Check for double bottom pattern."""
        try:
            # Look for two troughs of similar depth
            window = 20
            if len(df) < window:
                return False
                
            recent_data = df.tail(window)
            troughs = []
            
            for i in range(1, len(recent_data) - 1):
                if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1]):
                    troughs.append((i, recent_data['low'].iloc[i]))
                    
            if len(troughs) >= 2:
                # Check if the two lowest troughs are similar in depth
                troughs.sort(key=lambda x: x[1])
                depth_diff = abs(troughs[0][1] - troughs[1][1]) / troughs[0][1]
                return depth_diff < 0.02  # 2% difference threshold
                
            return False
        except Exception as e:
            logger.error(f"Error checking double bottom: {e}")
            return False
            
    def _check_head_and_shoulders(self, df: pd.DataFrame) -> bool:
        """Check for head and shoulders pattern."""
        try:
            window = 30
            if len(df) < window:
                return False
                
            recent_data = df.tail(window)
            peaks = []
            
            # Find all peaks
            for i in range(2, len(recent_data) - 2):
                if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                    peaks.append((i, recent_data['high'].iloc[i]))
                    
            if len(peaks) >= 3:
                # Check if the three highest peaks form a head and shoulders pattern
                peaks.sort(key=lambda x: x[1], reverse=True)
                if len(peaks) >= 3:
                    left_shoulder, head, right_shoulder = peaks[:3]
                    # Check if head is higher than shoulders
                    return (head[1] > left_shoulder[1] and 
                           head[1] > right_shoulder[1] and
                           abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < 0.02)
                    
            return False
        except Exception as e:
            logger.error(f"Error checking head and shoulders: {e}")
            return False
            
    def _check_inverse_head_and_shoulders(self, df: pd.DataFrame) -> bool:
        """Check for inverse head and shoulders pattern."""
        try:
            window = 30
            if len(df) < window:
                return False
                
            recent_data = df.tail(window)
            troughs = []
            
            # Find all troughs
            for i in range(2, len(recent_data) - 2):
                if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                    troughs.append((i, recent_data['low'].iloc[i]))
                    
            if len(troughs) >= 3:
                # Check if the three lowest troughs form an inverse head and shoulders pattern
                troughs.sort(key=lambda x: x[1])
                if len(troughs) >= 3:
                    left_shoulder, head, right_shoulder = troughs[:3]
                    # Check if head is lower than shoulders
                    return (head[1] < left_shoulder[1] and 
                           head[1] < right_shoulder[1] and
                           abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < 0.02)
                    
            return False
        except Exception as e:
            logger.error(f"Error checking inverse head and shoulders: {e}")
            return False 