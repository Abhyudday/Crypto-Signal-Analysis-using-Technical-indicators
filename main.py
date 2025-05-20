import logging
import asyncio
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from signal_broadcaster import SignalBroadcaster
from config import TELEGRAM_BOT_TOKEN

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)  # Add console handler
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.active_chats = set()  # Store active chat IDs
        self.signal_broadcasters = {}  # Store SignalBroadcaster instances for each chat
        logger.info("TradingBot initialized")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            logger.info(f"Received /start command from user {user.id} in {chat_type} chat {chat_id}")
            
            welcome_message = (
                f"👋 Welcome {user.first_name}!\n\n"
                "I'm your crypto trading signal bot. Use these commands:\n"
                "/monitor - Start receiving trading signals\n"
                "/stop - Stop receiving signals\n"
                "/help - Show this help message"
            )
            
            await context.bot.send_message(chat_id=chat_id, text=welcome_message)
            logger.info(f"Successfully sent welcome message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        try:
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            logger.info(f"Received /help command in {chat_type} chat {chat_id}")
            
            help_message = (
                "🤖 Crypto Trading Signal Bot\n\n"
                "Commands:\n"
                "/monitor - Start receiving trading signals\n"
                "/stop - Stop receiving signals\n"
                "/help - Show this help message\n\n"
                "The bot analyzes multiple cryptocurrencies and sends signals based on:\n"
                "• Technical Analysis (RSI, MACD, EMA, Bollinger Bands)\n"
                "• Chart Pattern Recognition\n"
                "• Market Sentiment Analysis"
            )
            await context.bot.send_message(chat_id=chat_id, text=help_message)
            logger.info(f"Successfully sent help message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}", exc_info=True)

    async def monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /monitor command"""
        try:
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            user = update.effective_user
            logger.info(f"Received /monitor command from user {user.id} in {chat_type} chat {chat_id}")

            if chat_id not in self.active_chats:
                self.active_chats.add(chat_id)
                self.signal_broadcasters[chat_id] = SignalBroadcaster(self, chat_id)
                await self.signal_broadcasters[chat_id].start_monitoring()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Started monitoring crypto markets. You'll receive signals when significant opportunities are detected."
                )
                logger.info(f"Successfully started monitoring for chat {chat_id}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Already monitoring markets for this chat."
                )
        except Exception as e:
            logger.error(f"Error in monitor command: {str(e)}", exc_info=True)

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stop command"""
        try:
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            logger.info(f"Received /stop command in {chat_type} chat {chat_id}")
            
            if chat_id in self.active_chats:
                self.active_chats.remove(chat_id)
                if chat_id in self.signal_broadcasters:
                    await self.signal_broadcasters[chat_id].stop_monitoring()
                    del self.signal_broadcasters[chat_id]
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🛑 Stopped monitoring markets for this chat."
                )
                logger.info(f"Successfully stopped monitoring for chat {chat_id}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Not currently monitoring markets for this chat."
                )
        except Exception as e:
            logger.error(f"Error in stop command: {str(e)}", exc_info=True)

    async def send_message(self, chat_id: int, message: str):
        """Send a message to a specific chat"""
        try:
            await self.application.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Successfully sent message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {str(e)}", exc_info=True)

    def run(self):
        """Run the bot"""
        try:
            # Check if token is available
            if not TELEGRAM_BOT_TOKEN:
                logger.error("TELEGRAM_BOT_TOKEN is not set!")
                sys.exit(1)
            
            logger.info("Starting bot...")
            logger.info(f"Bot token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")  # Log first and last 5 chars of token
            
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("monitor", self.monitor))
            self.application.add_handler(CommandHandler("stop", self.stop))

            # Start the bot
            logger.info("Starting polling...")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1) 