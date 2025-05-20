from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

# API Keys
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

EMA_SHORT = 9
EMA_LONG = 21

BB_PERIOD = 20
BB_STD = 2

# Pattern Recognition Parameters
DOUBLE_TOP_BOTTOM_THRESHOLD = 0.02  # 2% price difference threshold
HEAD_SHOULDERS_THRESHOLD = 0.03     # 3% price difference threshold
BREAKOUT_THRESHOLD = 0.01           # 1% breakout threshold

# Sentiment Analysis Parameters
SENTIMENT_THRESHOLD = 0.2           # Minimum sentiment score for signal
SENTIMENT_SAMPLE_SIZE = 100         # Number of tweets/posts to analyze

# Trading Parameters
SIGNAL_CONFIDENCE_THRESHOLD = 0.7   # Minimum confidence for trade execution
MAX_POSITION_SIZE = 0.1             # Maximum position size as fraction of portfolio
STOP_LOSS_PERCENTAGE = 0.02         # 2% stop loss
TAKE_PROFIT_PERCENTAGE = 0.04       # 4% take profit

# Timeframes
TIMEFRAME = '1h'                    # Default timeframe for analysis
HISTORY_PERIOD = '7d'               # Historical data period

# Signal Types
class SignalType:
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'

# Confidence Levels
class ConfidenceLevel:
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'
    NONE = 'NONE'

# Binance API Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Trading Configuration
TRADING_PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "XRPUSDT",
    "DOTUSDT",
    "DOGEUSDT"
]

# Technical Analysis Configuration
TECHNICAL_INDICATORS = [
    "RSI",
    "MACD",
    "EMA",
    "Bollinger Bands"
]

# Signal Configuration
SIGNAL_INTERVAL = 300  # Check for signals every 5 minutes
SENTIMENT_ANALYSIS_ENABLED = True  # Enable/disable sentiment analysis 