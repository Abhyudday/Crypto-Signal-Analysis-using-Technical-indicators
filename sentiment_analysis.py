import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import pandas as pd
from config import *
import time
import random

class SentimentAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_coin_gecko_news(self, symbol):
        """Get news from CoinGecko (free API)."""
        try:
            # Convert symbol to CoinGecko format (e.g., BTC/USDT -> bitcoin)
            coin_id = symbol.split('/')[0].lower()
            url = f"https://api.coingecko.com/api/v3/news?coin_id={coin_id}"
            
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                news = response.json()
                return [item['title'] + " " + item.get('description', '') for item in news]
            return []
        except Exception as e:
            print(f"Error fetching CoinGecko news: {e}")
            return []

    def get_crypto_panic_news(self, symbol):
        """Get news from CryptoPanic (free API)."""
        try:
            # Convert symbol to CryptoPanic format
            coin = symbol.split('/')[0].upper()
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token=free&currencies={coin}"
            
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                news = response.json()
                return [item['title'] + " " + item.get('description', '') for item in news['results']]
            return []
        except Exception as e:
            print(f"Error fetching CryptoPanic news: {e}")
            return []

    def get_coin_desk_news(self, symbol):
        """Scrape news from CoinDesk (free)."""
        try:
            # Convert symbol to CoinDesk format
            coin = symbol.split('/')[0].lower()
            url = f"https://www.coindesk.com/tag/{coin}/"
            
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                headlines = soup.find_all('h6', class_='card-title')
                return [headline.text.strip() for headline in headlines[:10]]
            return []
        except Exception as e:
            print(f"Error scraping CoinDesk news: {e}")
            return []

    def analyze_news_sentiment(self, news_items):
        """Analyze sentiment of news items."""
        sentiments = []
        for item in news_items:
            analysis = TextBlob(item)
            sentiments.append(analysis.sentiment.polarity)
        
        if sentiments:
            return sum(sentiments) / len(sentiments)
        return 0

    def get_sentiment_signal(self, sentiment_score):
        """Convert sentiment score to trading signal."""
        if sentiment_score > SENTIMENT_THRESHOLD:
            return SignalType.BUY, ConfidenceLevel.MEDIUM
        elif sentiment_score < -SENTIMENT_THRESHOLD:
            return SignalType.SELL, ConfidenceLevel.MEDIUM
        return SignalType.HOLD, ConfidenceLevel.NONE

    def analyze(self, symbol):
        """Analyze overall market sentiment using free sources."""
        # Get news from multiple sources
        news_items = []
        
        # CoinGecko news
        news_items.extend(self.get_coin_gecko_news(symbol))
        time.sleep(1)  # Rate limiting
        
        # CryptoPanic news
        news_items.extend(self.get_crypto_panic_news(symbol))
        time.sleep(1)  # Rate limiting
        
        # CoinDesk news
        news_items.extend(self.get_coin_desk_news(symbol))
        
        # Analyze sentiment
        if news_items:
            combined_sentiment = self.analyze_news_sentiment(news_items)
            return self.get_sentiment_signal(combined_sentiment)
        
        return SignalType.HOLD, ConfidenceLevel.NONE 