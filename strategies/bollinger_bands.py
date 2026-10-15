import pandas as pd
from typing import List, Dict
from strategies.base import BaseStrategy
from execution.order_types import OrderCreate, Position
from database.models import OrderSide, OrderType

class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Mean-Reversion Strategy.
    Buys when price touches/crosses below lower band.
    Sells when price touches/crosses above upper band.
    """
    def __init__(self, period: int = 20, std_dev: float = 2.0, fixed_qty: int = 10):
        self.period = period
        self.std_dev = std_dev
        self.fixed_qty = fixed_qty
        
    def generate_signals(self, data_slice: pd.DataFrame, current_positions: Dict[str, Position]) -> List[OrderCreate]:
        signals = []
        if len(data_slice) < self.period:
            return signals
            
        close_prices = data_slice['close']
        sma = close_prices.rolling(window=self.period).mean()
        std = close_prices.rolling(window=self.period).std()
        
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        current_price = close_prices.iloc[-1]
        prev_price = close_prices.iloc[-2]
        
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        symbol = data_slice.iloc[-1].get('symbol', 'UNKNOWN')
        pos = current_positions.get(symbol)
        current_qty = pos.quantity if pos else 0
        
        # Bullish (Mean Reversion from Bottom)
        if prev_price >= current_lower and current_price < current_lower:
            if current_qty <= 0:
                qty_to_buy = self.fixed_qty + abs(current_qty)
                signals.append(OrderCreate(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    quantity=qty_to_buy
                ))
                
        # Bearish (Mean Reversion from Top)
        elif prev_price <= current_upper and current_price > current_upper:
            if current_qty >= 0:
                qty_to_sell = self.fixed_qty + current_qty
                if qty_to_sell > 0:
                    signals.append(OrderCreate(
                        symbol=symbol,
                        order_type=OrderType.MARKET,
                        side=OrderSide.SELL,
                        quantity=qty_to_sell
                    ))
                    
        return signals
