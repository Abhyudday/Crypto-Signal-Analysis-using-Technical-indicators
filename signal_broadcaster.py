import asyncio
from datetime import datetime, timedelta
import pandas as pd
import logging
from config import *
from technical_analysis import TechnicalAnalyzer
from pattern_recognition import PatternRecognizer
from sentiment_analysis import SentimentAnalyzer
from core_types import SignalType, ConfidenceLevel

# Set up logging
logger = logging.getLogger(__name__)

class SignalBroadcaster:
    def __init__(self, bot: 'TradingBot', chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.sentiment_analyzer = SentimentAnalyzer()
        logger.info(f"Initialized SignalBroadcaster for chat_id: {chat_id}")
        
        # List of pairs to monitor
        self.pairs = [
            'BTC/USDT',
            'ETH/USDT',
            'BNB/USDT',
            'SOL/USDT',
            'ADA/USDT',
            'XRP/USDT',
            'DOT/USDT',
            'DOGE/USDT'
        ]
        
        # Store last signals to avoid duplicates
        self.last_signals = {}
        # Store last signal time for each pair
        self.last_signal_time = {}
        
        # Signal frequency settings
        self.MIN_SIGNAL_INTERVAL = 3600  # Minimum 1 hour between signals for each pair
        self.ANALYSIS_INTERVAL = 1     # Check every 1 second
        self.SIGNAL_EXPIRY = 7200       # Signals expire after 2 hours

    async def format_signal_message(self, symbol: str, signal: SignalType, confidence: ConfidenceLevel, df: pd.DataFrame) -> str:
        """Format the signal message for Telegram."""
        current_price = df['close'].iloc[-1]
        
        # Calculate entry and exit points based on current price
        if signal == SignalType.BUY:
            entry = current_price * 0.99  # 1% below current price
            stop_loss = current_price * 0.97  # 3% below current price
            take_profit = current_price * 1.03  # 3% above current price
        else:
            entry = current_price * 1.01  # 1% above current price
            stop_loss = current_price * 1.03  # 3% above current price
            take_profit = current_price * 0.97  # 3% below current price
            
        message = f"🔔 Trading Signal for {symbol}\n\n"
        message += f"Signal: {signal}\n"
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

    async def should_broadcast_signal(self, symbol: str, signal: SignalType) -> bool:
        """Check if we should broadcast a new signal."""
        current_time = datetime.now()
        
        # Check if we have a previous signal for this symbol
        if symbol in self.last_signals:
            last_signal_time, last_signal = self.last_signals[symbol]
            
            # Don't send if it's too soon after the last signal
            if (current_time - last_signal_time).total_seconds() < self.MIN_SIGNAL_INTERVAL:
                return False
                
            # Don't send if it's the same signal type
            if last_signal == signal:
                return False
                
            # Don't send if the last signal hasn't expired
            if (current_time - last_signal_time).total_seconds() < self.SIGNAL_EXPIRY:
                return False
                
        return True

    async def analyze_pair(self, symbol: str):
        """Analyze a trading pair and broadcast signal if conditions are met."""
        try:
            logger.info(f"Analyzing {symbol}...")
            # Get price data
            df = await self.bot.get_price_data(symbol)
            if df is None:
                logger.error(f"Failed to get price data for {symbol}")
                return
            
            # Get signals from all layers
            tech_signal, tech_conf = self.technical_analyzer.analyze(df)
            pattern_signal, pattern_conf = self.pattern_recognizer.analyze(df)
            sentiment_signal, sentiment_conf = self.sentiment_analyzer.analyze(symbol)
            
            logger.info(f"Signals for {symbol}: Technical={tech_signal}, Pattern={pattern_signal}, Sentiment={sentiment_signal}")
            
            # Count bullish and bearish signals
            bullish_count = sum(1 for signal in [tech_signal, pattern_signal, sentiment_signal] if signal == SignalType.BUY)
            bearish_count = sum(1 for signal in [tech_signal, pattern_signal, sentiment_signal] if signal == SignalType.SELL)
            
            # Determine final signal
            if bullish_count >= 2:
                final_signal = SignalType.BUY
                confidence = ConfidenceLevel.HIGH
            elif bearish_count >= 2:
                final_signal = SignalType.SELL
                confidence = ConfidenceLevel.HIGH
            elif bullish_count == 1:
                final_signal = SignalType.BUY
                confidence = ConfidenceLevel.MEDIUM
            elif bearish_count == 1:
                final_signal = SignalType.SELL
                confidence = ConfidenceLevel.MEDIUM
            else:
                final_signal = SignalType.HOLD
                confidence = ConfidenceLevel.NONE
            
            # Check if we should broadcast this signal
            if final_signal != SignalType.HOLD and await self.should_broadcast_signal(symbol, final_signal):
                message = await self.format_signal_message(symbol, final_signal, confidence, df)
                await self.bot.send_message(self.chat_id, message)
                self.last_signals[symbol] = (datetime.now(), final_signal)
                logger.info(f"Broadcasted {final_signal} signal for {symbol}")
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")

    async def start_monitoring(self):
        """Start monitoring all pairs."""
        logger.info(f"Starting monitoring for chat_id: {self.chat_id}")
        while True:
            try:
                for pair in self.pairs:
                    await self.analyze_pair(pair)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Wait before next round of analysis
                logger.info(f"Completed one round of analysis, waiting {self.ANALYSIS_INTERVAL} seconds...")
                await asyncio.sleep(self.ANALYSIS_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying 