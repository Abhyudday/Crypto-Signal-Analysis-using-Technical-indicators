import asyncio
import logging
from datetime import datetime
from typing import Dict, List
import aiohttp
import pandas as pd
import numpy as np
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    TELEGRAM_BOT_TOKEN,
    TRADING_PAIRS,
    TECHNICAL_INDICATORS,
    SENTIMENT_ANALYSIS_ENABLED,
    SIGNAL_INTERVAL
)

logger = logging.getLogger(__name__)

class SignalBroadcaster:
    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.running = False
        self.session = None
        self.last_signals: Dict[str, Dict] = {}

    async def start_monitoring(self):
        """Start monitoring markets and broadcasting signals"""
        self.running = True
        self.session = aiohttp.ClientSession()
        logger.info(f"Started monitoring for chat {self.chat_id}")
        
        while self.running:
            try:
                signals = await self.analyze_markets()
                if signals:
                    await self.broadcast_signals(signals)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            
            await asyncio.sleep(SIGNAL_INTERVAL)

    async def stop_monitoring(self):
        """Stop monitoring markets"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info(f"Stopped monitoring for chat {self.chat_id}")

    async def analyze_markets(self) -> List[Dict]:
        """Analyze markets and generate trading signals"""
        signals = []
        
        for pair in TRADING_PAIRS:
            try:
                # Get market data
                klines = await self.get_klines(pair)
                if not klines:
                    continue

                # Calculate technical indicators
                df = self.calculate_indicators(klines)
                
                # Generate signal
                signal = self.generate_signal(pair, df)
                if signal:
                    signals.append(signal)

            except Exception as e:
                logger.error(f"Error analyzing {pair}: {str(e)}")
                continue

        return signals

    async def get_klines(self, pair: str) -> List[Dict]:
        """Get kline/candlestick data from Binance"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                "symbol": pair,
                "interval": "1h",
                "limit": 100
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            "timestamp": k[0],
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5])
                        }
                        for k in data
                    ]
                else:
                    logger.error(f"Failed to get klines for {pair}: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting klines for {pair}: {str(e)}")
            return []

    def calculate_indicators(self, klines: List[Dict]) -> pd.DataFrame:
        """Calculate technical indicators"""
        df = pd.DataFrame(klines)
        
        # Calculate RSI
        if "RSI" in TECHNICAL_INDICATORS:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

        # Calculate MACD
        if "MACD" in TECHNICAL_INDICATORS:
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            df["MACD"] = exp1 - exp2
            df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

        # Calculate EMA
        if "EMA" in TECHNICAL_INDICATORS:
            df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
            df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

        # Calculate Bollinger Bands
        if "Bollinger Bands" in TECHNICAL_INDICATORS:
            df["SMA20"] = df["close"].rolling(window=20).mean()
            df["BB_upper"] = df["SMA20"] + 2 * df["close"].rolling(window=20).std()
            df["BB_lower"] = df["SMA20"] - 2 * df["close"].rolling(window=20).std()

        return df

    def generate_signal(self, pair: str, df: pd.DataFrame) -> Dict:
        """Generate trading signal based on technical analysis"""
        if df.empty:
            return None

        current_price = df["close"].iloc[-1]
        signal = {
            "pair": pair,
            "price": current_price,
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
            "action": None,
            "strength": 0
        }

        # RSI Analysis
        if "RSI" in df.columns:
            rsi = df["RSI"].iloc[-1]
            signal["indicators"]["RSI"] = rsi
            if rsi < 30:
                signal["action"] = "BUY"
                signal["strength"] += 1
            elif rsi > 70:
                signal["action"] = "SELL"
                signal["strength"] += 1

        # MACD Analysis
        if "MACD" in df.columns and "Signal" in df.columns:
            macd = df["MACD"].iloc[-1]
            signal_line = df["Signal"].iloc[-1]
            signal["indicators"]["MACD"] = macd
            if macd > signal_line:
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
            elif macd < signal_line:
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"

        # EMA Analysis
        if "EMA20" in df.columns and "EMA50" in df.columns:
            ema20 = df["EMA20"].iloc[-1]
            ema50 = df["EMA50"].iloc[-1]
            signal["indicators"]["EMA20"] = ema20
            signal["indicators"]["EMA50"] = ema50
            if ema20 > ema50:
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
            elif ema20 < ema50:
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"

        # Bollinger Bands Analysis
        if "BB_upper" in df.columns and "BB_lower" in df.columns:
            bb_upper = df["BB_upper"].iloc[-1]
            bb_lower = df["BB_lower"].iloc[-1]
            signal["indicators"]["BB_upper"] = bb_upper
            signal["indicators"]["BB_lower"] = bb_lower
            if current_price < bb_lower:
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
            elif current_price > bb_upper:
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"

        # Only return signals with sufficient strength
        if signal["action"] and signal["strength"] >= 2:
            return signal
        return None

    async def broadcast_signals(self, signals: List[Dict]):
        """Broadcast trading signals to the chat"""
        for signal in signals:
            try:
                # Format the signal message
                message = self.format_signal_message(signal)
                
                # Send the message
                await self.bot.send_message(self.chat_id, message)
                logger.info(f"Broadcasted signal for {signal['pair']} to chat {self.chat_id}")
                
            except Exception as e:
                logger.error(f"Error broadcasting signal: {str(e)}")

    def format_signal_message(self, signal: Dict) -> str:
        """Format the trading signal message"""
        action_emoji = "🟢" if signal["action"] == "BUY" else "🔴"
        strength_stars = "⭐" * signal["strength"]
        
        message = (
            f"{action_emoji} *{signal['action']} Signal* {action_emoji}\n\n"
            f"*Pair:* {signal['pair']}\n"
            f"*Price:* ${signal['price']:.2f}\n"
            f"*Strength:* {strength_stars}\n\n"
            f"*Technical Indicators:*\n"
        )

        # Add indicator values
        for indicator, value in signal["indicators"].items():
            if isinstance(value, float):
                message += f"• {indicator}: {value:.2f}\n"
            else:
                message += f"• {indicator}: {value}\n"

        message += f"\n*Time:* {signal['timestamp']}"
        return message 