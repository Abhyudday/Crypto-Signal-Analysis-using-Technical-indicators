# Crypto Trading Bot with Multi-Layered Signal Strategy

A modular Telegram-based crypto trading bot that implements a sophisticated multi-layered signal strategy combining technical analysis, pattern recognition, and sentiment analysis.

## Features

- **Technical Analysis Layer**
  - RSI, MACD, EMA, and Bollinger Bands indicators
  - Signal confluence detection
  - EMA crossover strategy

- **Pattern Recognition Layer**
  - Double top/bottom detection
  - Head and Shoulders pattern recognition
  - Support/Resistance breakout detection

- **Sentiment Analysis Layer**
  - Real-time social media sentiment analysis
  - News sentiment aggregation
  - Sentiment-based confidence scoring

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

3. Run the bot:
```bash
python main.py
```

## Project Structure

- `main.py` - Main bot entry point
- `technical_analysis.py` - Technical indicators and analysis
- `pattern_recognition.py` - Chart pattern detection
- `sentiment_analysis.py` - Social media and news sentiment analysis
- `config.py` - Configuration and constants
- `utils.py` - Utility functions

## Signal Logic

The bot generates trading signals based on the confluence of:
1. Technical indicators (3+ indicators must align)
2. Chart pattern recognition
3. Market sentiment analysis

Signal confidence levels:
- HIGH: All layers align (technical + pattern + sentiment)
- MEDIUM: Two layers align
- LOW: Single layer signal
- NO SIGNAL: No clear direction 