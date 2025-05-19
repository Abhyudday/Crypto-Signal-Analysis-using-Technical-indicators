import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
import asyncio
import signal
import sys

from technical_analysis import TechnicalAnalyzer
from pattern_recognition import PatternRecognizer
from sentiment_analysis import SentimentAnalyzer
from signal_broadcaster import SignalBroadcaster
from config import *
from core_types import SignalType, ConfidenceLevel

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Global application instance
application = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal. Cleaning up...")
    if application:
        asyncio.run(application.stop())
    sys.exit(0)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    try:
        logger.info(f"Received /start command from user {update.effective_user.id}")
        await update.message.reply_text(
            "Welcome to the Crypto Trading Bot! 🚀\n\n"
            "Available commands:\n"
            "/analyze <symbol> - Analyze a cryptocurrency (e.g., /analyze BTC/USDT)\n"
            "/monitor - Start monitoring all pairs in this chat\n"
            "/stop_monitor - Stop monitoring in this chat\n"
            "/help - Show this help message"
        )
        logger.info("Successfully sent welcome message")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /analyze command."""
    try:
        logger.info(f"Received /analyze command from user {update.effective_user.id}")
        if not context.args:
            await update.message.reply_text("Please provide a symbol (e.g., /analyze BTC/USDT)")
            return
            
        symbol = context.args[0].upper()
        logger.info(f"Analyzing symbol: {symbol}")
        await update.message.reply_text(f"Analyzing {symbol}... Please wait.")
        
        bot = TradingBot()
        df = await bot.get_price_data(symbol)
        
        if df is None:
            logger.error(f"Failed to fetch price data for {symbol}")
            await update.message.reply_text("Error fetching price data. Please try again later.")
            return
            
        signal, confidence = bot.analyze_market(df, symbol)
        message = bot.format_signal_message(symbol, signal, confidence, df)
        
        await update.message.reply_text(message)
        logger.info(f"Successfully sent analysis for {symbol}")
    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await update.message.reply_text("Sorry, there was an error analyzing the symbol. Please try again.")

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start monitoring all pairs in the current chat."""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logger.info(f"Received /monitor command from user {user_id} in chat {chat_id}")
        
        if chat_id in context.bot_data.get('broadcasters', {}):
            logger.info(f"Monitoring already active in chat {chat_id}")
            await update.message.reply_text("Monitoring is already active in this chat.")
            return
        
        bot = TradingBot()
        broadcaster = SignalBroadcaster(bot, chat_id)
        
        # Store broadcaster in bot_data
        if 'broadcasters' not in context.bot_data:
            context.bot_data['broadcasters'] = {}
        context.bot_data['broadcasters'][chat_id] = broadcaster
        
        # Start monitoring in background
        asyncio.create_task(broadcaster.start_monitoring())
        
        await update.message.reply_text(
            "✅ Started monitoring all pairs in this chat.\n"
            "You will receive automatic signals when trading opportunities are detected."
        )
        logger.info(f"Successfully started monitoring for chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in monitor command: {e}")
        await update.message.reply_text("Sorry, there was an error starting the monitoring. Please try again.")

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop monitoring in the current chat."""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logger.info(f"Received /stop_monitor command from user {user_id} in chat {chat_id}")
        
        if chat_id in context.bot_data.get('broadcasters', {}):
            del context.bot_data['broadcasters'][chat_id]
            logger.info(f"Stopped monitoring in chat {chat_id}")
            await update.message.reply_text("Stopped monitoring in this chat.")
        else:
            logger.info(f"No active monitoring in chat {chat_id}")
            await update.message.reply_text("No active monitoring in this chat.")
    except Exception as e:
        logger.error(f"Error in stop_monitor command: {e}")
        await update.message.reply_text("Sorry, there was an error stopping the monitoring. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    try:
        logger.info(f"Received /help command from user {update.effective_user.id}")
        await update.message.reply_text(
            "🤖 Crypto Trading Bot Help\n\n"
            "Commands:\n"
            "/analyze <symbol> - Analyze a cryptocurrency\n"
            "Example: /analyze BTC/USDT\n\n"
            "/monitor - Start automatic monitoring of all pairs\n"
            "/stop_monitor - Stop automatic monitoring\n\n"
            "The bot uses multiple analysis layers:\n"
            "1. Technical Analysis (RSI, MACD, EMA, BB)\n"
            "2. Pattern Recognition\n"
            "3. Market Sentiment\n\n"
            "Signals are generated based on the confluence of these factors."
        )
        logger.info("Successfully sent help message")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("Sorry, there was an error showing the help message. Please try again.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any message that is not a command."""
    try:
        logger.info(f"Received message from user {update.effective_user.id}: {update.message.text}")
        await update.message.reply_text(
            "Please use one of the available commands:\n"
            "/start - Start the bot\n"
            "/help - Show help message\n"
            "/analyze <symbol> - Analyze a cryptocurrency\n"
            "/monitor - Start monitoring\n"
            "/stop_monitor - Stop monitoring"
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")

class TradingBot:
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.exchange = ccxt.binance()
        self.broadcasters = {}
        self.MIN_SIGNAL_INTERVAL = 3600  # Change this to adjust minimum time between signals
        self.ANALYSIS_INTERVAL = 900     # Change this to adjust how often the bot checks
        self.SIGNAL_EXPIRY = 7200       # Change this to adjust how long signals remain valid
        
    async def send_message(self, chat_id: int, message: str) -> None:
        """Send a message to a specific chat."""
        try:
            if application:
                await application.bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Successfully sent message to chat {chat_id}")
            else:
                logger.error("Application instance not available for sending message")
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
            raise
        
    async def get_price_data(self, symbol, timeframe='1h', limit=100):
        """Fetch historical price data from exchange."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            return None

    def analyze_market(self, df, symbol):
        """Combine all analysis layers and generate final signal."""
        # Technical Analysis
        tech_signal, tech_conf = self.technical_analyzer.analyze(df)
        
        # Pattern Recognition
        pattern_signal, pattern_conf = self.pattern_recognizer.analyze(df)
        
        # Sentiment Analysis
        sentiment_signal, sentiment_conf = self.sentiment_analyzer.analyze(symbol)
        
        # Combine signals
        signals = {
            'technical': (tech_signal, tech_conf),
            'pattern': (pattern_signal, pattern_conf),
            'sentiment': (sentiment_signal, sentiment_conf)
        }
        
        # Count bullish and bearish signals
        bullish_count = sum(1 for signal, _ in signals.values() if signal == SignalType.BUY)
        bearish_count = sum(1 for signal, _ in signals.values() if signal == SignalType.SELL)
        
        # Determine final signal and confidence
        if bullish_count >= 2:
            return SignalType.BUY, ConfidenceLevel.HIGH
        elif bearish_count >= 2:
            return SignalType.SELL, ConfidenceLevel.HIGH
        elif bullish_count == 1:
            return SignalType.BUY, ConfidenceLevel.MEDIUM
        elif bearish_count == 1:
            return SignalType.SELL, ConfidenceLevel.MEDIUM
        else:
            return SignalType.HOLD, ConfidenceLevel.NONE

    def format_signal_message(self, symbol, signal, confidence, df):
        """Format trading signal message for Telegram."""
        current_price = df['close'].iloc[-1]
        message = f"🔔 Trading Signal for {symbol}\n\n"
        message += f"Signal: {signal}\n"
        message += f"Confidence: {confidence}\n"
        message += f"Current Price: ${current_price:.2f}\n\n"
        
        # Add technical indicators
        message += "📊 Technical Indicators:\n"
        message += f"RSI: {self.technical_analyzer.indicators['rsi'].iloc[-1]:.2f}\n"
        message += f"MACD: {self.technical_analyzer.indicators['macd'].iloc[-1]:.2f}\n"
        message += f"EMA (9/21): {self.technical_analyzer.indicators['ema_short'].iloc[-1]:.2f}/{self.technical_analyzer.indicators['ema_long'].iloc[-1]:.2f}\n"
        
        return message

def main():
    """Start the bot."""
    global application
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Add error handler
        application.add_error_handler(error_handler)

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("analyze", analyze))
        application.add_handler(CommandHandler("monitor", monitor))
        application.add_handler(CommandHandler("stop_monitor", stop_monitor))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add message handler for non-command messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 