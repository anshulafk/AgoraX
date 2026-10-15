import pandas as pd
from typing import List, Dict
from strategies.base import BaseStrategy
from execution.order_types import OrderCreate, Position
from database.models import OrderSide, OrderType

class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    Buys when Fast SMA crosses above Slow SMA.
    Sells when Fast SMA crosses below Slow SMA.
    """
    def __init__(self, fast_period: int = 10, slow_period: int = 50, fixed_qty: int = 10):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fixed_qty = fixed_qty
        
    def generate_signals(self, data_slice: pd.DataFrame, current_positions: Dict[str, Position]) -> List[OrderCreate]:
        signals = []
        
        if len(data_slice) < self.slow_period:
            return signals # Not enough data
            
        # Calculate moving averages
        close_prices = data_slice['close']
        fast_sma = close_prices.rolling(window=self.fast_period).mean()
        slow_sma = close_prices.rolling(window=self.slow_period).mean()
        
        current_fast = fast_sma.iloc[-1]
        current_slow = slow_sma.iloc[-1]
        prev_fast = fast_sma.iloc[-2]
        prev_slow = slow_sma.iloc[-2]
        
        symbol = data_slice.iloc[-1].get('symbol', 'UNKNOWN')
        pos = current_positions.get(symbol)
        current_qty = pos.quantity if pos else 0
        
        # Bullish Crossover
        if prev_fast <= prev_slow and current_fast > current_slow:
            if current_qty <= 0: # Not long
                # Cover short if exists + go long
                qty_to_buy = self.fixed_qty + abs(current_qty)
                signals.append(OrderCreate(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    quantity=qty_to_buy
                ))
                
        # Bearish Crossover
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if current_qty >= 0: # Not short
                # Sell long if exists + go short
                qty_to_sell = self.fixed_qty + current_qty
                if qty_to_sell > 0:
                    signals.append(OrderCreate(
                        symbol=symbol,
                        order_type=OrderType.MARKET,
                        side=OrderSide.SELL,
                        quantity=qty_to_sell
                    ))
                    
        return signals
