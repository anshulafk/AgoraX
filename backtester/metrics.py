import pandas as pd
import numpy as np

class PerformanceMetrics:
    """
    Calculates quantitative performance metrics for a backtest run.
    """
    
    @staticmethod
    def calculate_cagr(initial_capital: float, final_capital: float, trading_days: int) -> float:
        """Compound Annual Growth Rate"""
        if trading_days == 0:
            return 0.0
        years = trading_days / 252.0
        cagr = (final_capital / initial_capital) ** (1 / years) - 1
        return round(cagr, 4)

    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.07) -> float:
        """
        Assumes daily returns and an annualized Indian risk-free rate of ~7%.
        """
        if returns.empty or returns.std() == 0:
            return 0.0
        
        daily_rf = risk_free_rate / 252.0
        excess_returns = returns - daily_rf
        sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
        return round(sharpe, 4)

    @staticmethod
    def calculate_max_drawdown(equity_curve: pd.Series) -> float:
        """
        Calculates the maximum peak-to-trough decline.
        """
        if equity_curve.empty:
            return 0.0
            
        rolling_max = equity_curve.cummax()
        drawdowns = (equity_curve - rolling_max) / rolling_max
        max_dd = drawdowns.min()
        return round(abs(max_dd), 4)

    @staticmethod
    def calculate_trade_metrics(trades: pd.DataFrame) -> dict:
        """
        Calculates win rate and profit factor based on realized trade PnL.
        """
        if trades.empty or 'pnl' not in trades.columns:
            return {"win_rate": 0.0, "profit_factor": 0.0, "total_trades": 0}
            
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        gross_profit = winning_trades['pnl'].sum()
        gross_loss = abs(losing_trades['pnl'].sum())
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "total_trades": total_trades
        }
