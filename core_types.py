from enum import Enum, auto
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SignalType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'

class ConfidenceLevel(Enum):
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    NONE = 'NONE'

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', 0))

# Trading Configuration
DEFAULT_TIMEFRAME = '1h'
DEFAULT_LIMIT = 100

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

EMA_SHORT = 9
EMA_LONG = 21

# Pattern Recognition Parameters
DOUBLE_TOP_BOTTOM_THRESHOLD = 0.02  # 2% threshold for double top/bottom patterns
HEAD_SHOULDERS_THRESHOLD = 0.03     # 3% threshold for head and shoulders patterns

# Signal Broadcasting Parameters
MIN_SIGNAL_INTERVAL = 3600  # Minimum 1 hour between signals
ANALYSIS_INTERVAL = 1      # Check every 1 second
SIGNAL_EXPIRY = 7200      # Signals expire after 2 hours

# Trading Pairs to Monitor
TRADING_PAIRS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'ADA/USDT',
    'XRP/USDT',
    'DOT/USDT',
    'DOGE/USDT'
]

# API Keys
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET') 