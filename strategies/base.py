from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict
from execution.order_types import OrderCreate, Position

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Forces all strategies to implement a standard signal generation interface.
    """
    
    @abstractmethod
    def generate_signals(self, data_slice: pd.DataFrame, current_positions: Dict[str, Position]) -> List[OrderCreate]:
        """
        Evaluates market data and current portfolio state to generate Orders.
        
        Args:
            data_slice (pd.DataFrame): Historical OHLCV data up to current timestamp.
            current_positions (Dict[str, Position]): Current active positions in portfolio.
            
        Returns:
            List[OrderCreate]: List of order intents to submit to the broker.
        """
        pass
