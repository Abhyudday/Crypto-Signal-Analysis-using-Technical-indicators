import logging
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import pandas as pd
from core_types import SignalType, ConfidenceLevel, TWITTER_API_KEY, TWITTER_API_SECRET, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import time
import random

# Set up logging
logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        self.twitter_api_key = TWITTER_API_KEY
        self.twitter_api_secret = TWITTER_API_SECRET
        self.reddit_client_id = REDDIT_CLIENT_ID
        self.reddit_client_secret = REDDIT_CLIENT_SECRET
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.info("Initialized SentimentAnalyzer")

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

    def analyze(self, symbol: str) -> tuple[SignalType, ConfidenceLevel]:
        """Analyze market sentiment for a given symbol."""
        try:
            # Get news sentiment
            news_sentiment = self._analyze_news(symbol)
            
            # Get social media sentiment
            social_sentiment = self._analyze_social_media(symbol)
            
            # Combine sentiments
            combined_sentiment = (news_sentiment + social_sentiment) / 2
            
            # Determine signal and confidence
            if combined_sentiment > 0.3:
                return SignalType.BUY, ConfidenceLevel.HIGH
            elif combined_sentiment < -0.3:
                return SignalType.SELL, ConfidenceLevel.HIGH
            elif combined_sentiment > 0.1:
                return SignalType.BUY, ConfidenceLevel.MEDIUM
            elif combined_sentiment < -0.1:
                return SignalType.SELL, ConfidenceLevel.MEDIUM
            else:
                return SignalType.HOLD, ConfidenceLevel.NONE
                
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return SignalType.HOLD, ConfidenceLevel.NONE

    def _analyze_news(self, symbol: str) -> float:
        """Analyze news sentiment for a given symbol."""
        try:
            # Get news from crypto news APIs
            news_url = f"https://cryptopanic.com/api/v1/posts/?auth_token=YOUR_API_KEY&currencies={symbol.split('/')[0]}"
            response = requests.get(news_url)
            news_data = response.json()
            
            # Analyze sentiment of news headlines
            sentiments = []
            for news in news_data.get('results', []):
                text = news.get('title', '')
                if text:
                    blob = TextBlob(text)
                    sentiments.append(blob.sentiment.polarity)
            
            # Return average sentiment
            return sum(sentiments) / len(sentiments) if sentiments else 0
            
        except Exception as e:
            logger.error(f"Error analyzing news: {e}")
            return 0

    def _analyze_social_media(self, symbol: str) -> float:
        """Analyze social media sentiment for a given symbol."""
        try:
            # Get tweets about the symbol
            tweets = self._get_tweets(symbol)
            
            # Get Reddit posts about the symbol
            reddit_posts = self._get_reddit_posts(symbol)
            
            # Analyze sentiment of tweets and Reddit posts
            sentiments = []
            
            # Analyze tweets
            for tweet in tweets:
                blob = TextBlob(tweet)
                sentiments.append(blob.sentiment.polarity)
            
            # Analyze Reddit posts
            for post in reddit_posts:
                blob = TextBlob(post)
                sentiments.append(blob.sentiment.polarity)
            
            # Return average sentiment
            return sum(sentiments) / len(sentiments) if sentiments else 0
            
        except Exception as e:
            logger.error(f"Error analyzing social media: {e}")
            return 0

    def _get_tweets(self, symbol: str) -> list[str]:
        """Get recent tweets about a symbol."""
        try:
            # This is a placeholder - you would need to implement actual Twitter API calls
            # using the twitter_api_key and twitter_api_secret
            return []
        except Exception as e:
            logger.error(f"Error getting tweets: {e}")
            return []

    def _get_reddit_posts(self, symbol: str) -> list[str]:
        """Get recent Reddit posts about a symbol."""
        try:
            # This is a placeholder - you would need to implement actual Reddit API calls
            # using the reddit_client_id and reddit_client_secret
            return []
        except Exception as e:
            logger.error(f"Error getting Reddit posts: {e}")
            return [] 