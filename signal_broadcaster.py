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
        self.last_signals: Dict[str, Dict] = {}  # Store last signal for each pair
        self.signal_cooldown = 7200  # 2 hours in seconds
        self.profit_tracking: Dict[str, Dict] = {}  # Track profits for each signal
        logger.info(f"SignalBroadcaster initialized for chat {chat_id}")

    async def start_monitoring(self):
        """Start monitoring markets and broadcasting signals"""
        self.running = True
        self.session = aiohttp.ClientSession()
        logger.info(f"Started monitoring for chat {self.chat_id}")
        
        # Start profit tracking in background
        asyncio.create_task(self.update_profit_tracking())
        
        while self.running:
            try:
                logger.info("Starting market analysis cycle...")
                signals = await self.analyze_markets()
                if signals:
                    logger.info(f"Found {len(signals)} signals to broadcast")
                    await self.broadcast_signals(signals)
                else:
                    logger.info("No signals found in this cycle")
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
            
            logger.info(f"Waiting {SIGNAL_INTERVAL} seconds before next analysis cycle...")
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
                logger.info(f"Analyzing {pair}...")
                # Get market data
                klines = await self.get_klines(pair)
                if not klines:
                    logger.warning(f"No klines data received for {pair}")
                    continue

                logger.info(f"Received {len(klines)} klines for {pair}")
                # Calculate technical indicators
                df = self.calculate_indicators(klines)
                
                # Generate signal
                signal = self.generate_signal(pair, df)
                if signal:
                    logger.info(f"Generated {signal['action']} signal for {pair} with strength {signal['strength']}")
                    signals.append(signal)
                else:
                    logger.info(f"No signal generated for {pair}")

            except Exception as e:
                logger.error(f"Error analyzing {pair}: {str(e)}", exc_info=True)
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
            
            logger.info(f"Fetching klines for {pair}...")
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched klines for {pair}")
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
            logger.error(f"Error getting klines for {pair}: {str(e)}", exc_info=True)
            return []

    def calculate_indicators(self, klines: List[Dict]) -> pd.DataFrame:
        """Calculate technical indicators"""
        logger.info("Calculating technical indicators...")
        df = pd.DataFrame(klines)
        
        # Calculate RSI
        if "RSI" in TECHNICAL_INDICATORS:
            logger.info("Calculating RSI...")
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

        # Calculate MACD
        if "MACD" in TECHNICAL_INDICATORS:
            logger.info("Calculating MACD...")
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            df["MACD"] = exp1 - exp2
            df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

        # Calculate EMA
        if "EMA" in TECHNICAL_INDICATORS:
            logger.info("Calculating EMA...")
            df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
            df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

        # Calculate Bollinger Bands
        if "Bollinger Bands" in TECHNICAL_INDICATORS:
            logger.info("Calculating Bollinger Bands...")
            df["SMA20"] = df["close"].rolling(window=20).mean()
            df["BB_upper"] = df["SMA20"] + 2 * df["close"].rolling(window=20).std()
            df["BB_lower"] = df["SMA20"] - 2 * df["close"].rolling(window=20).std()

        logger.info("Technical indicators calculation completed")
        return df

    def generate_signal(self, pair: str, df: pd.DataFrame) -> Dict:
        """Generate trading signal based on technical analysis"""
        if df.empty:
            logger.warning(f"Empty dataframe for {pair}")
            return None

        current_price = df["close"].iloc[-1]
        current_time = datetime.now().timestamp()

        # Check if we're in cooldown period for this pair
        if pair in self.last_signals:
            last_signal_time = self.last_signals[pair].get('timestamp', 0)
            if current_time - last_signal_time < self.signal_cooldown:
                logger.info(f"Signal for {pair} is in cooldown period")
                return None

        signal = {
            "pair": pair,
            "price": current_price,
            "timestamp": current_time,
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
                logger.info(f"RSI buy signal for {pair}: {rsi:.2f}")
            elif rsi > 70:
                signal["action"] = "SELL"
                signal["strength"] += 1
                logger.info(f"RSI sell signal for {pair}: {rsi:.2f}")

        # MACD Analysis
        if "MACD" in df.columns and "Signal" in df.columns:
            macd = df["MACD"].iloc[-1]
            signal_line = df["Signal"].iloc[-1]
            signal["indicators"]["MACD"] = macd
            if macd > signal_line and macd > 0:  # Added condition for stronger signals
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
                logger.info(f"MACD buy signal for {pair}: {macd:.2f} > {signal_line:.2f}")
            elif macd < signal_line and macd < 0:  # Added condition for stronger signals
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"
                logger.info(f"MACD sell signal for {pair}: {macd:.2f} < {signal_line:.2f}")

        # EMA Analysis
        if "EMA20" in df.columns and "EMA50" in df.columns:
            ema20 = df["EMA20"].iloc[-1]
            ema50 = df["EMA50"].iloc[-1]
            signal["indicators"]["EMA20"] = ema20
            signal["indicators"]["EMA50"] = ema50
            if ema20 > ema50 and current_price > ema20:  # Added price condition
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
                logger.info(f"EMA buy signal for {pair}: {ema20:.2f} > {ema50:.2f}")
            elif ema20 < ema50 and current_price < ema20:  # Added price condition
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"
                logger.info(f"EMA sell signal for {pair}: {ema20:.2f} < {ema50:.2f}")

        # Bollinger Bands Analysis
        if "BB_upper" in df.columns and "BB_lower" in df.columns:
            bb_upper = df["BB_upper"].iloc[-1]
            bb_lower = df["BB_lower"].iloc[-1]
            signal["indicators"]["BB_upper"] = bb_upper
            signal["indicators"]["BB_lower"] = bb_lower
            if current_price < bb_lower and df["close"].iloc[-2] < df["close"].iloc[-1]:  # Added trend confirmation
                if signal["action"] == "BUY":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "BUY"
                logger.info(f"BB buy signal for {pair}: {current_price:.2f} < {bb_lower:.2f}")
            elif current_price > bb_upper and df["close"].iloc[-2] > df["close"].iloc[-1]:  # Added trend confirmation
                if signal["action"] == "SELL":
                    signal["strength"] += 1
                elif signal["action"] is None:
                    signal["action"] = "SELL"
                logger.info(f"BB sell signal for {pair}: {current_price:.2f} > {bb_upper:.2f}")

        # Only return signals with sufficient strength and matching action
        if signal["action"] and signal["strength"] >= 2:
            # Store the signal for cooldown tracking
            self.last_signals[pair] = signal
            # Initialize profit tracking for this signal
            self.profit_tracking[pair] = {
                "entry_price": current_price,
                "entry_time": current_time,
                "action": signal["action"]
            }
            logger.info(f"Strong {signal['action']} signal generated for {pair} with strength {signal['strength']}")
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
                logger.error(f"Error broadcasting signal: {str(e)}", exc_info=True)

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

        # Add profit tracking if available
        if signal["pair"] in self.profit_tracking:
            tracking = self.profit_tracking[signal["pair"]]
            if "current_profit" in tracking:
                profit_emoji = "📈" if tracking["current_profit"] > 0 else "📉"
                message += f"\n*Profit/Loss:* {profit_emoji} {tracking['current_profit']:.2f}%"

        return message

    async def update_profit_tracking(self):
        """Update profit tracking for active signals"""
        while self.running:
            try:
                for pair, tracking in self.profit_tracking.items():
                    current_time = datetime.now().timestamp()
                    # Only track for 24 hours
                    if current_time - tracking["entry_time"] > 86400:  # 24 hours
                        del self.profit_tracking[pair]
                        continue

                    # Get current price
                    klines = await self.get_klines(pair)
                    if not klines:
                        continue

                    current_price = float(klines[-1]["close"])
                    entry_price = tracking["entry_price"]
                    action = tracking["action"]

                    # Calculate profit/loss
                    if action == "BUY":
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                    else:  # SELL
                        profit_pct = ((entry_price - current_price) / entry_price) * 100

                    # Update profit tracking
                    tracking["current_profit"] = profit_pct
                    tracking["current_price"] = current_price

            except Exception as e:
                logger.error(f"Error updating profit tracking: {str(e)}", exc_info=True)

            await asyncio.sleep(300)  # Update every 5 minutes 