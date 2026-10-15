from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import logging
from database.connection import SessionLocal
from database.models import BacktestRun
import pandas as pd
from typing import List

logger = logging.getLogger(__name__)

app = FastAPI(title="AlgoTrade-India API", version="1.0.0")

class StrategyRequest(BaseModel):
    strategy_name: str
    symbol: str = "RELIANCE.NS"
    timeframe: str = "1m"
    period: str = "5d"

@app.get("/")
def read_root():
    return {"status": "AlgoTrade-India Engine is running. Ready for incoming commands."}

@app.get("/metrics", tags=["Performance"])
def get_latest_metrics():
    """Returns the latest backtest run metrics from the database."""
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).order_by(BacktestRun.id.desc()).first()
        if not run:
            return {"message": "No backtest runs found."}
        return {
            "strategy": run.strategy_name,
            "initial_capital": run.initial_capital,
            "final_capital": run.final_capital,
            "sharpe_ratio": run.sharpe_ratio,
            "max_drawdown": run.max_drawdown
        }
    finally:
        db.close()

@app.post("/backtest/run", tags=["Control"])
def run_backtest_endpoint(req: StrategyRequest, background_tasks: BackgroundTasks):
    """
    Triggers a backtest run in the background. 
    In a fully fleshed out system, this would accept custom params and spawn the `BacktestEngine`.
    """
    # For now, we just validate the request
    allowed_strategies = ["SMACrossoverStrategy", "RSIMomentumStrategy", "BollingerBandsStrategy"]
    if req.strategy_name not in allowed_strategies:
        raise HTTPException(status_code=400, detail=f"Strategy must be one of {allowed_strategies}")
        
    # Example of how you'd dispatch the job to celery or a background thread:
    # background_tasks.add_task(run_backtest_job, req)
    
    return {"message": f"Backtest for {req.strategy_name} on {req.symbol} queued successfully."}

@app.get("/live/status", tags=["Live"])
def live_engine_status():
    """Check if the live paper-trading websocket engine is running."""
    # Placeholder for live engine state check
    return {"status": "inactive", "message": "Live mode requires websocket consumer to be started via CLI."}
