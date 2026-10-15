import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import sys
from pathlib import Path

# Ensure the root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from config.settings import settings
from data.historical import fetch_historical_data
from backtester.engine import BacktestEngine
from strategies.sma_crossover import SMACrossoverStrategy
from strategies.rsi_momentum import RSIMomentumStrategy
from strategies.bollinger_bands import BollingerBandsStrategy

st.set_page_config(page_title="AlgoTrade-India Dashboard", layout="wide", page_icon="📈")

@st.cache_resource
def get_db_engine():
    return create_engine(settings.DATABASE_URL)

db_engine = get_db_engine()

# --- Pre-defined Indian Stocks ---
stocks = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "TATAMOTORS.NS": "Tata Motors",
    "ZOMATO.NS": "Zomato Ltd"
}

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Backtest Controls")
selected_symbol = st.sidebar.selectbox("Select Stock", list(stocks.keys()), format_func=lambda x: f"{x} ({stocks[x]})")
strategy_name = st.sidebar.selectbox("Select Strategy", ["SMA Crossover", "RSI Momentum", "Bollinger Bands"])

if st.sidebar.button("▶️ Run Backtest"):
    with st.spinner(f"Fetching data and running backtest for {stocks[selected_symbol]}..."):
        # Fetch 5 days of 1-minute data for the selected stock
        data = fetch_historical_data(selected_symbol, interval="1m", period="5d")
        if not data.empty:
            if strategy_name == "SMA Crossover":
                strategy = SMACrossoverStrategy(fast_period=5, slow_period=20, fixed_qty=10)
            elif strategy_name == "RSI Momentum":
                strategy = RSIMomentumStrategy(period=14, overbought=70, oversold=30, fixed_qty=10)
            else:
                strategy = BollingerBandsStrategy(period=20, std_dev=2.0, fixed_qty=10)
                
            engine = BacktestEngine(strategy=strategy, historical_data=data)
            engine.run()
            st.sidebar.success(f"Backtest complete for {selected_symbol}!")
        else:
            st.sidebar.error("Failed to fetch data from Yahoo Finance.")

st.title("📈 AlgoTrade-India Engine")
st.markdown("Interactive backtesting with realistic Indian tax models and charts.")

# --- Fetch Latest Run ---
try:
    df_runs = pd.read_sql("SELECT * FROM backtest_runs ORDER BY id DESC LIMIT 1", db_engine)
    if not df_runs.empty:
        run = df_runs.iloc[0]
        
        # Header Metrics
        col1, col2, col3, col4 = st.columns(4)
        profit = run['final_capital'] - run['initial_capital']
        col1.metric("Final Capital", f"₹{run['final_capital']:,.2f}", f"{profit:+,.2f} INR")
        col2.metric("Sharpe Ratio", f"{run['sharpe_ratio']:.2f}")
        col3.metric("Max Drawdown", f"{run['max_drawdown'] * 100:.2f}%")
        col4.metric("Strategy", run['strategy_name'])
        
        st.divider()

        # --- Charting ---
        st.header(f"📊 OHLCV Chart & Trade Signals")
        # Fetch the historical data again to plot it (since it's cached on disk, it's fast)
        chart_data = fetch_historical_data(selected_symbol, interval="1m", period="5d")
        
        if not chart_data.empty:
            fig = go.Figure(data=[go.Candlestick(x=chart_data.index,
                open=chart_data['open'],
                high=chart_data['high'],
                low=chart_data['low'],
                close=chart_data['close'],
                name="OHLC")])
                
            # Fetch trades from the database to overlay as Buy/Sell markers
            df_trades = pd.read_sql(f"SELECT * FROM trades WHERE symbol='{selected_symbol}' ORDER BY timestamp", db_engine)
            
            if not df_trades.empty:
                buys = df_trades[df_trades['side'] == 'BUY']
                sells = df_trades[df_trades['side'] == 'SELL']
                
                fig.add_trace(go.Scatter(x=buys['timestamp'], y=buys['price'], mode='markers', name='Buy Signal', 
                                         marker=dict(color='#00ff00', symbol='triangle-up', size=12)))
                fig.add_trace(go.Scatter(x=sells['timestamp'], y=sells['price'], mode='markers', name='Sell Signal', 
                                         marker=dict(color='#ff0000', symbol='triangle-down', size=12)))

            fig.update_layout(
                title=f"{stocks[selected_symbol]} ({selected_symbol}) Price Action", 
                xaxis_rangeslider_visible=False, 
                height=600, 
                template="plotly_dark",
                yaxis_title="Price (INR)",
                xaxis_title="Time"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        st.divider()

        # --- Trades Table ---
        st.header("Trade Execution & Tax Breakdown")
        df_trades_recent = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50", db_engine)
        if not df_trades_recent.empty:
            total_taxes = df_trades_recent['total_tax'].sum()
            st.write(f"**Total Capital Lost to Taxes/Fees in recent trades:** ₹{total_taxes:,.2f}")
            st.dataframe(df_trades_recent, use_container_width=True)
            
    else:
        st.info("No backtest runs found. Use the sidebar to select a stock and run a backtest!")
except Exception as e:
    st.error(f"Error rendering dashboard: {e}")
