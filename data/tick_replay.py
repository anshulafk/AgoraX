import asyncio
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MarketReplaySimulator:
    """
    Simulates real-time live trading by replaying historical tick/candle data
    with an adjustable speed multiplier. Great for off-hours testing.
    """
    def __init__(self, historical_data: pd.DataFrame, speed_multiplier: float = 1.0):
        # We expect a DatetimeIndex
        self.data = historical_data.sort_index()
        self.speed_multiplier = speed_multiplier
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    async def start_replay(self):
        logger.info(f"Starting market replay simulator at {self.speed_multiplier}x speed...")
        prev_time = None
        
        for timestamp, row in self.data.iterrows():
            if prev_time is not None:
                # Calculate real-time delta between ticks/candles
                time_diff = (timestamp - prev_time).total_seconds()
                wait_time = time_diff / self.speed_multiplier
                
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # Synthesize a tick event from OHLCV
            # In a real tick replay we'd use raw tick data, here we use candle close for demo
            tick_data = {
                "symbol": row.name if "symbol" not in row else row["symbol"],
                "timestamp": timestamp.isoformat(),
                "price": row["close"],
                "volume": row.get("volume", 0)
            }

            for callback in self.callbacks:
                await callback(tick_data)
            
            prev_time = timestamp
