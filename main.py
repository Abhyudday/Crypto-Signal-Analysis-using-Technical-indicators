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
import os
from dotenv import load_dotenv
from aiohttp import web

from technical_analysis import TechnicalAnalyzer
from pattern_recognition import PatternRecognizer
from sentiment_analysis import SentimentAnalyzer
from signal_broadcaster import SignalBroadcaster
from config import *
from core_types import SignalType, ConfidenceLevel, TELEGRAM_BOT_TOKEN

# Load environment variables
load_dotenv()

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

# Initialize bot and broadcaster
bot = TradingBot()
broadcaster = SignalBroadcaster(bot)

# Store active monitoring tasks
active_monitors = {}

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
    """Start command handler."""
    chat_id = update.effective_chat.id
    if chat_id in active_monitors:
        await update.message.reply_text("Monitoring is already active for this chat.")
        return
        
    # Start monitoring for this chat
    task = asyncio.create_task(broadcaster.start_monitoring(chat_id))
    active_monitors[chat_id] = task
    
    await update.message.reply_text(
        "🚀 Trading bot started!\n\n"
        "I will monitor the following pairs:\n" +
        "\n".join(f"• {pair}" for pair in broadcaster.pairs) +
        "\n\nI'll send you signals when I detect high-confidence trading opportunities."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop command handler."""
    chat_id = update.effective_chat.id
    if chat_id not in active_monitors:
        await update.message.reply_text("No active monitoring for this chat.")
        return
        
    # Cancel the monitoring task
    active_monitors[chat_id].cancel()
    del active_monitors[chat_id]
    
    await update.message.reply_text("🛑 Trading bot stopped. Use /start to resume monitoring.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command handler."""
    chat_id = update.effective_chat.id
    is_active = chat_id in active_monitors
    
    status_text = "✅ Active" if is_active else "❌ Inactive"
    
    await update.message.reply_text(
        f"🤖 Bot Status: {status_text}\n\n"
        f"Monitoring pairs:\n" +
        "\n".join(f"• {pair}" for pair in broadcaster.pairs)
    )

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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    try:
        logger.info(f"Received /help command from user {update.effective_user.id}")
        await update.message.reply_text(
            "🤖 Crypto Trading Bot Help\n\n"
            "Commands:\n"
            "/analyze <symbol> - Analyze a cryptocurrency\n"
            "Example: /analyze BTC/USDT\n\n"
            "/start - Start automatic monitoring of all pairs\n"
            "/stop - Stop automatic monitoring\n\n"
            "/status - Check bot status\n\n"
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
            "/status - Check bot status"
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
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.application = None
        self.signal_broadcaster = None
        self.chat_id = int(os.getenv('TELEGRAM_CHAT_ID', 0))
        
    async def send_message(self, chat_id: int, message: str) -> None:
        """Send a message to a specific chat."""
        try:
            if self.application:
                await self.application.bot.send_message(chat_id=chat_id, text=message)
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

    async def start(self, update, context):
        """Send a message when the command /start is issued."""
        await update.message.reply_text('Crypto Signal Bot is running!')
        
    async def help(self, update, context):
        """Send a message when the command /help is issued."""
        help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/status - Check bot status
        """
        await update.message.reply_text(help_text)
        
    async def status(self, update, context):
        """Send bot status."""
        status_text = "Bot is running and monitoring crypto signals!"
        await update.message.reply_text(status_text)
        
    async def error_handler(self, update, context):
        """Log the error and send a message to the user."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred while processing your request."
            )

    async def health_check(self, request):
        """Health check endpoint for Railway."""
        return web.Response(text="OK")

    def run(self):
        """Start the bot."""
        try:
            # Create the Application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("status", self.status))
            
            # Add error handler
            self.application.add_error_handler(self.error_handler)
            
            # Initialize signal broadcaster
            self.signal_broadcaster = SignalBroadcaster(self, self.chat_id)
            
            # Start the bot
            logger.info("Starting bot...")
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

async def start_web_server():
    """Start the web server for health checks."""
    app = web.Application()
    app.router.add_get('/health', TradingBot().health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()

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
        application.add_handler(CommandHandler("status", status))
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
    # Start the web server in a separate task
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    
    # Start the bot
    bot = TradingBot()
    bot.run() 