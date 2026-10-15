import pandas as pd
from typing import List, Dict
from strategies.base import BaseStrategy
from execution.order_types import OrderCreate, Position
from database.models import OrderSide, OrderType

class RSIMomentumStrategy(BaseStrategy):
    """
    RSI Mean Reversion/Momentum Strategy.
    Buys when RSI dips below oversold threshold and starts recovering.
    Sells when RSI peaks above overbought threshold and starts dropping.
    """
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30, fixed_qty: int = 10):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.fixed_qty = fixed_qty
        
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, data_slice: pd.DataFrame, current_positions: Dict[str, Position]) -> List[OrderCreate]:
        signals = []
        if len(data_slice) < self.period + 1:
            return signals
            
        rsi = self._calculate_rsi(data_slice['close'])
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        symbol = data_slice.iloc[-1].get('symbol', 'UNKNOWN')
        pos = current_positions.get(symbol)
        current_qty = pos.quantity if pos else 0
        
        # Bullish: Crosses back above oversold line
        if prev_rsi <= self.oversold and current_rsi > self.oversold:
            if current_qty <= 0:
                qty_to_buy = self.fixed_qty + abs(current_qty)
                signals.append(OrderCreate(
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    quantity=qty_to_buy
                ))
                
        # Bearish: Crosses back below overbought line
        elif prev_rsi >= self.overbought and current_rsi < self.overbought:
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
