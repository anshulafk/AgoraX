import os
import yfinance as yf
import pandas as pd
from pathlib import Path
from config.settings import settings, BASE_DIR

CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

def fetch_historical_data(symbol: str, interval: str = "1m", period: str = "5d") -> pd.DataFrame:
    """
    Fetches historical OHLCV data from yfinance and caches it to disk.
    """
    # Safe filename
    safe_symbol = symbol.replace("^", "").replace(".", "_")
    cache_file = CACHE_DIR / f"{safe_symbol}_{interval}_{period}.csv"
    
    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col="timestamp", parse_dates=True)
        if "symbol" not in df.columns:
            df["symbol"] = symbol
        return df
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    
    if not df.empty:
        # Standardize column names
        df.columns = [col.lower() for col in df.columns]
        df.index.name = "timestamp"
        df["symbol"] = symbol
        
        # Save to cache
        df.to_csv(cache_file)
        
    return df
