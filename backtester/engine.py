import logging
import pandas as pd
from datetime import datetime
from database.connection import SessionLocal
from database.models import BacktestRun
from execution.paper_broker import PaperBroker
from risk.risk_guard import RiskGuard
from backtester.metrics import PerformanceMetrics
from config.settings import config_yaml

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Core engine that simulates the passage of time over historical data,
    feeding price updates to the broker, checking risk guards, and calculating
    performance metrics.
    """
    def __init__(self, strategy, historical_data: pd.DataFrame):
        self.strategy = strategy
        self.data = historical_data.sort_index()
        self.initial_capital = config_yaml['strategy']['initial_capital']
        
        self.db = SessionLocal()
        self.broker = PaperBroker(initial_capital=self.initial_capital, db=self.db)
        self.risk_guard = RiskGuard(initial_daily_capital=self.initial_capital)
        self.equity_curve = []
        
    def run(self):
        logger.info(f"Starting backtest for {self.strategy.__class__.__name__}")
        
        current_day = None
        
        for timestamp, row in self.data.iterrows():
            current_date = timestamp.date()
            if current_day != current_date:
                # New day: update daily capital for the risk guard's drawdown check
                self.risk_guard.initial_daily_capital = self.broker.current_capital
                current_day = current_date
            
            # 1. Update broker with new price (Simulating tick matching)
            current_price = row['close']
            symbol = row.get('symbol', 'UNKNOWN')
            
            self.broker.process_tick(symbol, current_price)
            
            # 2. Track total equity (Cash + Unrealized PnL)
            unrealized_pnl = sum(pos.unrealized_pnl for pos in self.broker.positions.values())
            total_equity = self.broker.current_capital + unrealized_pnl
            
            # 3. Check Risk Limits
            if self.risk_guard.check_drawdown_halt(self.broker.current_capital, unrealized_pnl):
                # Reached max daily drawdown limit, halt new signals for today
                pass
            elif self.risk_guard.is_square_off_time(timestamp):
                # 15:15 IST - time to close all intraday positions
                # Placeholder for submitting counter market orders
                pass 
            else:
                # 4. Generate Strategy Signals
                # The strategy inspects the data slice up to current timestamp
                data_slice = self.data.loc[:timestamp]
                signals = self.strategy.generate_signals(data_slice, self.broker.positions)
                
                # 5. Submit orders to the broker
                for signal in signals:
                    self.broker.submit_order(signal)
                
            # Record Equity Curve
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': total_equity
            })
            
        logger.info("Backtest complete. Calculating metrics...")
        self._finalize_run()
        
    def _finalize_run(self):
        df_equity = pd.DataFrame(self.equity_curve)
        if df_equity.empty:
            logger.warning("No equity curve data generated.")
            self.db.close()
            return
            
        df_equity.set_index('timestamp', inplace=True)
        # Resample to daily equity to calculate daily returns properly
        daily_equity = df_equity['equity'].resample('D').last().dropna()
        daily_returns = daily_equity.pct_change().fillna(0)
        
        trading_days = len(daily_equity)
        
        final_capital = self.broker.current_capital # Assuming all positions closed at end
        cagr = PerformanceMetrics.calculate_cagr(self.initial_capital, final_capital, trading_days)
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(daily_returns)
        max_dd = PerformanceMetrics.calculate_max_drawdown(df_equity['equity'])
        
        # Save run metrics to DB
        run_record = BacktestRun(
            strategy_name=self.strategy.__class__.__name__,
            start_time=self.data.index.min(),
            end_time=self.data.index.max(),
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd
        )
        self.db.add(run_record)
        self.db.commit()
        
        logger.info(f"--- BACKTEST RESULTS ---")
        logger.info(f"Final Capital : ₹{final_capital:,.2f}")
        logger.info(f"CAGR          : {cagr:.2%}")
        logger.info(f"Sharpe Ratio  : {sharpe:.2f}")
        logger.info(f"Max Drawdown  : {max_dd:.2%}")
        
        self.db.close()
