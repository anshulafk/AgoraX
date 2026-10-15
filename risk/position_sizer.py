from config.settings import config_yaml
import math

class PositionSizer:
    @staticmethod
    def calculate_quantity(capital: float, current_price: float, stop_loss_price: float) -> int:
        """
        Fixed fractional risk-per-trade position sizing.
        Ensures we don't risk more than the allowed percentage of current capital.
        """
        if stop_loss_price <= 0 or current_price <= 0:
            return 0
            
        risk_per_trade_pct = config_yaml['risk']['max_risk_per_trade_pct']
        max_capital_at_risk = capital * risk_per_trade_pct
        
        risk_per_share = abs(current_price - stop_loss_price)
        
        if risk_per_share == 0:
            return 0
            
        quantity = math.floor(max_capital_at_risk / risk_per_share)
        
        # Ensure we don't exceed absolute buying power (rough estimate without margin)
        max_affordable_qty = math.floor(capital / current_price)
        
        return min(quantity, max_affordable_qty)

    @staticmethod
    def fixed_quantity(capital: float, current_price: float, percentage_of_capital: float = 0.1) -> int:
        """
        Allocates a fixed percentage of total capital to a single trade.
        """
        allocated_capital = capital * percentage_of_capital
        return math.floor(allocated_capital / current_price)
