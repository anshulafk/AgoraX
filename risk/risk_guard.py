from datetime import datetime
import pytz
from config.settings import config_yaml

class RiskGuard:
    """
    Monitors daily drawdown limits and handles mandatory intraday square-off logic.
    """
    
    def __init__(self, initial_daily_capital: float):
        self.initial_daily_capital = initial_daily_capital
        self.max_drawdown_pct = config_yaml['risk']['max_daily_drawdown_pct']
        
        square_off_str = config_yaml['risk']['square_off_time_ist']
        hour, minute = map(int, square_off_str.split(":"))
        self.square_off_hour = hour
        self.square_off_minute = minute
        
        self.ist_tz = pytz.timezone('Asia/Kolkata')

    def check_drawdown_halt(self, current_capital: float, unrealized_pnl: float) -> bool:
        """
        Returns True if trading should be halted due to excessive drawdown.
        """
        total_equity = current_capital + unrealized_pnl
        drawdown = (self.initial_daily_capital - total_equity) / self.initial_daily_capital
        
        return drawdown >= self.max_drawdown_pct

    def is_square_off_time(self, current_time: datetime = None) -> bool:
        """
        Returns True if it's time to force square-off all open intraday positions.
        """
        if current_time is None:
            current_time = datetime.now(self.ist_tz)
        else:
            # If naive, assume UTC for backtesting, then convert to IST
            if current_time.tzinfo is None:
                current_time = pytz.utc.localize(current_time)
            current_time = current_time.astimezone(self.ist_tz)
                
        if current_time.hour > self.square_off_hour:
            return True
        if current_time.hour == self.square_off_hour and current_time.minute >= self.square_off_minute:
            return True
            
        return False
