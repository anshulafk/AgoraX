import argparse
import logging
from database.connection import Base, engine
from data.historical import fetch_historical_data
from backtester.engine import BacktestEngine
from strategies.sma_crossover import SMACrossoverStrategy
from config.settings import config_yaml

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")

def setup_database():
    """Creates all ORM tables in the database if they don't exist."""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ready.")

def run_backtest():
    """Runs a historical backtest for a specific symbol using the YAML config."""
    # We will pick the first symbol in the config as a default demo
    symbol = config_yaml['strategy']['symbols'][0]
    timeframe = config_yaml['strategy']['timeframe']
    
    logger.info(f"Fetching historical data for {symbol} at {timeframe} timeframe...")
    # Fetching 5 days of 1-minute data for a quick test
    data = fetch_historical_data(symbol, interval=timeframe, period="5d")
    
    if data.empty:
        logger.error("Failed to fetch historical data. Exiting backtest.")
        return
        
    # Instantiate our SMA crossover strategy
    # Since we are using 1m data for 5 days, let's use small SMA windows to ensure crossovers
    strategy = SMACrossoverStrategy(fast_period=5, slow_period=20, fixed_qty=10)
    
    # Initialize and run the backtester
    engine = BacktestEngine(strategy=strategy, historical_data=data)
    engine.run()

def run_live():
    """Placeholder for Live Paper-Trading Mode."""
    logger.info("Live trading mode requires the API and Websocket loops (Coming Next!).")
    
def run_api():
    """Placeholder for API server."""
    logger.info("API server mode requires FastAPI setup (Coming Next!).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlgoTrade-India Execution Engine")
    parser.add_argument("--mode", type=str, required=True, choices=["backtest", "live", "api"], 
                        help="Operating mode: backtest, live, or api")
    
    args = parser.parse_args()
    
    # Ensure database tables exist
    setup_database()
    
    if args.mode == "backtest":
        run_backtest()
    elif args.mode == "live":
        run_live()
    elif args.mode == "api":
        run_api()
