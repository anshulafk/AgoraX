import pandas as pd
from typing import Dict, Any

class BarAggregator:
    """
    Resamples raw asynchronous ticks into structured OHLCV candles
    at a specified timeframe.
    """
    def __init__(self, timeframe: str = "1min"):
        self.timeframe = timeframe
        self.ticks = []

    def add_tick(self, tick: Dict[str, Any]):
        self.ticks.append(tick)

    def get_aggregated_bars(self) -> pd.DataFrame:
        if not self.ticks:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.ticks)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample logic
        resampled = df.resample(self.timeframe).agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': 'sum'
        })
        
        # Flatten MultiIndex columns from agg
        resampled.columns = ['open', 'high', 'low', 'close', 'volume']
        return resampled.dropna()
