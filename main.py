import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from signal_broadcaster import SignalBroadcaster
from config import TELEGRAM_BOT_TOKEN

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='trading_bot.log'
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.active_chats = set()  # Store active chat IDs
        self.signal_broadcasters = {}  # Store SignalBroadcaster instances for each chat

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"Received /start command from user {user.id}")
        
        welcome_message = (
            f"👋 Welcome {user.first_name}!\n\n"
            "I'm your crypto trading signal bot. Use these commands:\n"
            "/monitor - Start receiving trading signals\n"
            "/stop - Stop receiving signals\n"
            "/help - Show this help message"
        )
        
        await context.bot.send_message(chat_id=chat_id, text=welcome_message)
        logger.info("Successfully sent welcome message")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        chat_id = update.effective_chat.id
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

    async def monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /monitor command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"Received /monitor command from user {user.id} in chat {chat_id}")

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

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stop command"""
        chat_id = update.effective_chat.id
        if chat_id in self.active_chats:
            self.active_chats.remove(chat_id)
            if chat_id in self.signal_broadcasters:
                await self.signal_broadcasters[chat_id].stop_monitoring()
                del self.signal_broadcasters[chat_id]
            await context.bot.send_message(
                chat_id=chat_id,
                text="🛑 Stopped monitoring markets for this chat."
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Not currently monitoring markets for this chat."
            )

    async def send_message(self, chat_id: int, message: str):
        """Send a message to a specific chat"""
        try:
            await self.application.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {str(e)}")

    def run(self):
        """Run the bot"""
        logger.info("Starting bot...")
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("monitor", self.monitor))
        self.application.add_handler(CommandHandler("stop", self.stop))

        # Start the bot
        self.application.run_polling()

if __name__ == "__main__":
    bot = TradingBot()
    bot.run() 