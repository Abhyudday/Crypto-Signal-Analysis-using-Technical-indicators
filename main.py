import logging
import asyncio
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from signal_broadcaster import SignalBroadcaster
from config import TELEGRAM_BOT_TOKEN
import telegram


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout) 
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.active_chats = set() 
        self.signal_broadcasters = {} 
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
                # Send initial confirmation
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔄 Starting market monitoring... Please wait while I initialize the analysis."
                )
                
                self.active_chats.add(chat_id)
                self.signal_broadcasters[chat_id] = SignalBroadcaster(self, chat_id)
                
                # Start monitoring in the background
                asyncio.create_task(self.signal_broadcasters[chat_id].start_monitoring())
                
                # Send detailed confirmation message
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ Market monitoring started!\n\n"
                        "I'm now analyzing these pairs:\n"
                        "• BTC/USDT\n"
                        "• ETH/USDT\n"
                        "• BNB/USDT\n"
                        "• SOL/USDT\n"
                        "• ADA/USDT\n"
                        "• XRP/USDT\n"
                        "• DOT/USDT\n"
                        "• DOGE/USDT\n\n"
                        "I'll send signals when I detect significant opportunities based on:\n"
                        "• RSI (Relative Strength Index)\n"
                        "• MACD (Moving Average Convergence Divergence)\n"
                        "• EMA (Exponential Moving Averages)\n"
                        "• Bollinger Bands\n\n"
                        "Use /stop to stop monitoring."
                    )
                )
                logger.info(f"Successfully started monitoring for chat {chat_id}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Already monitoring markets for this chat.\n\n"
                        "I'm actively analyzing the markets and will send signals when I detect opportunities.\n"
                        "Use /stop if you want to stop receiving signals."
                    )
                )
        except Exception as e:
            logger.error(f"Error in monitor command: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, there was an error starting the monitoring. Please try again later."
            )

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stop command"""
        try:
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            logger.info(f"Received /stop command in {chat_type} chat {chat_id}")
            
            if chat_id in self.active_chats:
                # Send initial confirmation
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔄 Stopping market monitoring... Please wait."
                )
                
                self.active_chats.remove(chat_id)
                if chat_id in self.signal_broadcasters:
                    await self.signal_broadcasters[chat_id].stop_monitoring()
                    del self.signal_broadcasters[chat_id]
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ Market monitoring stopped!\n\n"
                        "I'm no longer analyzing the markets for this chat.\n"
                        "Use /monitor to start receiving signals again."
                    )
                )
                logger.info(f"Successfully stopped monitoring for chat {chat_id}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "ℹ️ Not currently monitoring markets for this chat.\n\n"
                        "Use /monitor to start receiving trading signals."
                    )
                )
        except Exception as e:
            logger.error(f"Error in stop command: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, there was an error stopping the monitoring. Please try again later."
            )

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
            if not TELEGRAM_BOT_TOKEN:
                logger.error("TELEGRAM_BOT_TOKEN is not set!")
                sys.exit(1)
            
            logger.info("Starting bot...")
            logger.info(f"Bot token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")  
            
            # Create application with cleanup
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("monitor", self.monitor))
            self.application.add_handler(CommandHandler("stop", self.stop))
            
            # Add error handler
            self.application.add_error_handler(self.error_handler)
            
            logger.info("Starting polling...")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            sys.exit(1)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the bot"""
        try:
            logger.error(f"Exception while handling an update: {context.error}")
            
            # If it's a conflict error, try to clean up
            if isinstance(context.error, telegram.error.Conflict):
                logger.info("Detected conflict error, attempting to clean up...")
                try:
                    await self.application.bot.delete_webhook()
                    await asyncio.sleep(1)  # Wait a bit before retrying
                except Exception as e:
                    logger.error(f"Error during cleanup: {str(e)}")
            
            # Notify user if possible
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ Sorry, I encountered an error. Please try again in a moment."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        # Ensure we're the only instance running
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 5000))
        
        bot = TradingBot()
        bot.run()
    except socket.error:
        logger.error("Another instance of the bot is already running!")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            sock.close()
        except:
            pass 