import asyncio
from datetime import datetime, timedelta
import pandas as pd
import logging
from config import *
from technical_analysis import TechnicalAnalyzer
from pattern_recognition import PatternRecognizer
from sentiment_analysis import SentimentAnalyzer
from core_types import SignalType, ConfidenceLevel
import time

# Set up logging
logger = logging.getLogger(__name__)

class SignalBroadcaster:
    def __init__(self, bot: 'TradingBot'):
        self.bot = bot
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.sentiment_analyzer = SentimentAnalyzer()
        logger.info("Initialized SignalBroadcaster")
        
        # List of pairs to monitor
        self.pairs = TRADING_PAIRS
        
        # Store last signals to avoid duplicates
        self.last_signals = {}
        # Store last signal time for each pair
        self.last_signal_time = {}
        
        # Signal frequency settings
        self.MIN_SIGNAL_INTERVAL = MIN_SIGNAL_INTERVAL
        self.ANALYSIS_INTERVAL = ANALYSIS_INTERVAL
        self.SIGNAL_EXPIRY = SIGNAL_EXPIRY

    async def format_signal_message(self, symbol: str, signal_type: SignalType, confidence: ConfidenceLevel, df: pd.DataFrame) -> str:
        """Format the signal message for Telegram."""
        current_price = df['close'].iloc[-1]
        
        # Calculate entry and exit points based on current price
        if signal_type == SignalType.BUY:
            entry = current_price * 0.99  # 1% below current price
            stop_loss = current_price * 0.97  # 3% below current price
            take_profit = current_price * 1.03  # 3% above current price
        else:
            entry = current_price * 1.01  # 1% above current price
            stop_loss = current_price * 1.03  # 3% above current price
            take_profit = current_price * 0.97  # 3% below current price
            
        message = f"🔔 Trading Signal for {symbol}\n\n"
        message += f"Signal: {signal_type}\n"
        message += f"Confidence: {confidence}\n"
        message += f"Current Price: ${current_price:.2f}\n\n"
        
        # Add technical indicators
        message += "📊 Technical Indicators:\n"
        message += f"RSI: {self.technical_analyzer.indicators['rsi'].iloc[-1]:.2f}\n"
        message += f"MACD: {self.technical_analyzer.indicators['macd'].iloc[-1]:.2f}\n"
        message += f"EMA (9/21): {self.technical_analyzer.indicators['ema_short'].iloc[-1]:.2f}/{self.technical_analyzer.indicators['ema_long'].iloc[-1]:.2f}\n\n"
        
        # Add entry and exit points
        message += "🎯 Trading Levels:\n"
        message += f"Entry: ${entry:.2f}\n"
        message += f"Stop Loss: ${stop_loss:.2f}\n"
        message += f"Take Profit: ${take_profit:.2f}\n\n"
        
        # Add disclaimer
        message += "⚠️ Disclaimer: This is not financial advice. Always do your own research before trading."
        
        return message

    def should_broadcast_signal(self, chat_id: int, signal_type: SignalType, confidence: ConfidenceLevel) -> bool:
        """Determine if a signal should be broadcast based on timing and confidence."""
        current_time = time.time()
        
        # Don't send signals if confidence is not HIGH
        if confidence != ConfidenceLevel.HIGH:
            return False
            
        # Check if enough time has passed since last signal for this chat
        if chat_id in self.last_signal_time and (current_time - self.last_signal_time[chat_id]) < self.MIN_SIGNAL_INTERVAL:
            return False
            
        # Check if this is a different signal type than the last one for this chat
        if chat_id in self.last_signals and self.last_signals[chat_id] == signal_type:
            return False
            
        return True

    async def analyze_pair(self, symbol: str, chat_id: int):
        """Analyze a trading pair and broadcast signals if conditions are met."""
        try:
            # Get price data
            df = await self.bot.get_price_data(symbol)
            if df is None or df.empty:
                logger.error(f"Failed to get price data for {symbol}")
                return
                
            # Get signals from all three analysis layers
            # These are all synchronous functions, no await needed
            technical_signal, technical_confidence = self.technical_analyzer.analyze(df)
            pattern_signal, pattern_confidence = self.pattern_recognizer.analyze(df)
            sentiment_signal, sentiment_confidence = self.sentiment_analyzer.analyze(symbol)
            
            # Log all signals
            logger.info(f"{symbol} - Technical: {technical_signal} ({technical_confidence})")
            logger.info(f"{symbol} - Pattern: {pattern_signal} ({pattern_confidence})")
            logger.info(f"{symbol} - Sentiment: {sentiment_signal} ({sentiment_confidence})")
            
            # Count bullish and bearish signals
            bullish_count = 0
            bearish_count = 0
            
            # Only count signals with HIGH confidence
            if technical_confidence == ConfidenceLevel.HIGH:
                if technical_signal == SignalType.BUY:
                    bullish_count += 1
                elif technical_signal == SignalType.SELL:
                    bearish_count += 1
                    
            if pattern_confidence == ConfidenceLevel.HIGH:
                if pattern_signal == SignalType.BUY:
                    bullish_count += 1
                elif pattern_signal == SignalType.SELL:
                    bearish_count += 1
                    
            if sentiment_confidence == ConfidenceLevel.HIGH:
                if sentiment_signal == SignalType.BUY:
                    bullish_count += 1
                elif sentiment_signal == SignalType.SELL:
                    bearish_count += 1
            
            # Determine final signal
            final_signal = SignalType.HOLD
            final_confidence = ConfidenceLevel.NONE
            
            # Only generate a signal if we have at least 2 HIGH confidence signals in the same direction
            if bullish_count >= 2:
                final_signal = SignalType.BUY
                final_confidence = ConfidenceLevel.HIGH
            elif bearish_count >= 2:
                final_signal = SignalType.SELL
                final_confidence = ConfidenceLevel.HIGH
            
            # Check if we should broadcast this signal
            if self.should_broadcast_signal(chat_id, final_signal, final_confidence):
                # Format the message (this is a synchronous function)
                message = await self.format_signal_message(
                    symbol=symbol,
                    signal_type=final_signal,
                    confidence=final_confidence,
                    df=df
                )
                
                # Send the message (this is an async function)
                await self.bot.send_message(chat_id, message)
                
                # Update last signal info for this chat
                self.last_signal_time[chat_id] = time.time()
                self.last_signals[chat_id] = final_signal
                
                logger.info(f"Broadcast signal for {symbol} to chat {chat_id}: {final_signal} ({final_confidence})")
            else:
                logger.info(f"Skipping signal broadcast for {symbol} to chat {chat_id} - conditions not met")
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")

    async def start_monitoring(self, chat_id: int):
        """Start monitoring all pairs for a specific chat."""
        logger.info(f"Starting monitoring for chat_id: {chat_id}")
        while True:
            try:
                for pair in self.pairs:
                    await self.analyze_pair(pair, chat_id)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Wait before next round of analysis
                logger.info(f"Completed one round of analysis for chat {chat_id}, waiting {self.ANALYSIS_INTERVAL} seconds...")
                await asyncio.sleep(self.ANALYSIS_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring loop for chat {chat_id}: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying 