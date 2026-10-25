import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
import sys as _sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# ── Path bootstrap ────────────────────────────────────────────────────────────
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in _sys.path:
    _sys.path.append(str(root_dir))

from config.settings import settings, config_yaml
from data.historical import fetch_historical_data
from backtester.engine import BacktestEngine
from strategies.sma_crossover import SMACrossoverStrategy
from strategies.rsi_momentum import RSIMomentumStrategy
from strategies.bollinger_bands import BollingerBandsStrategy

# ── Constants ─────────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
INITIAL_CAPITAL = config_yaml["strategy"]["initial_capital"]

STRATEGY_META = {
    "SMA Crossover": {
        "icon": "📉",
        "color": "#6C63FF",
        "description": "Trend-following · Buys on golden cross, sells on death cross",
        "params": {"fast_period": 5, "slow_period": 20, "fixed_qty": 10},
    },
    "RSI Momentum": {
        "icon": "⚡",
        "color": "#00D4AA",
        "description": "Mean-reversion · RSI 14 · Oversold <30, Overbought >70",
        "params": {"period": 14, "overbought": 70, "oversold": 30, "fixed_qty": 10},
    },
    "Bollinger Bands": {
        "icon": "🎯",
        "color": "#FF6B6B",
        "description": "Volatility bands · Buys at lower band, sells at upper band",
        "params": {"period": 20, "std_dev": 2.0, "fixed_qty": 10},
    },
}

STOCKS = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "TATAMOTORS.NS": "Tata Motors",
    "ZOMATO.NS": "Zomato",
    "WIPRO.NS": "Wipro",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "SBI",
    "ADANIENT.NS": "Adani Enterprises",
    "^NSEI": "Nifty 50 Index",
    "^NSEBANK": "Bank Nifty Index",
}

# ── Page Config & Global CSS ──────────────────────────────────────────────────
st.set_page_config(
    page_title="AgoraX · Trading Workstation",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary:    #0D0F14;
    --bg-secondary:  #141720;
    --bg-card:       #1A1E2E;
    --bg-card-hover: #1F2438;
    --border:        #252A3A;
    --accent-purple: #6C63FF;
    --accent-green:  #00D4AA;
    --accent-red:    #FF6B6B;
    --accent-amber:  #FFB347;
    --text-primary:  #E8EAED;
    --text-secondary:#8B9099;
    --text-muted:    #555C6E;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.main .block-container {
    padding: 1.5rem 2rem 2rem 2rem !important;
    max-width: 1600px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}

/* Header Bar */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.25rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 1.25rem;
}
.header-brand {
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #6C63FF 0%, #00D4AA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.market-open {
    display: inline-flex; align-items: center; gap: 0.4rem;
    font-size: 0.72rem; font-weight: 600;
    color: var(--accent-green);
    background: rgba(0,212,170,0.08);
    border: 1px solid rgba(0,212,170,0.25);
    padding: 0.3rem 0.75rem; border-radius: 20px;
    letter-spacing: 0.06em; text-transform: uppercase;
}
.market-closed {
    display: inline-flex; align-items: center; gap: 0.4rem;
    font-size: 0.72rem; font-weight: 600;
    color: var(--text-muted);
    background: rgba(85,92,110,0.12);
    border: 1px solid rgba(85,92,110,0.3);
    padding: 0.3rem 0.75rem; border-radius: 20px;
    letter-spacing: 0.06em; text-transform: uppercase;
}
.header-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; color: var(--text-muted);
}

/* KPI Cards */
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    position: relative; overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: #353A50; }
.kpi-label {
    font-size: 0.7rem; font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 0.45rem;
}
.kpi-value {
    font-size: 1.55rem; font-weight: 700;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}
.kpi-delta-pos  { font-size:0.8rem; font-weight:600; color:var(--accent-green); margin-top:0.3rem; }
.kpi-delta-neg  { font-size:0.8rem; font-weight:600; color:var(--accent-red);   margin-top:0.3rem; }
.kpi-delta-zero { font-size:0.8rem; font-weight:600; color:var(--text-muted);   margin-top:0.3rem; }
.kpi-accent-bar {
    position:absolute; left:0; top:0; bottom:0; width:3px;
    border-radius:12px 0 0 12px;
}

/* Strategy Cards */
.strat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    transition: border-color 0.2s, background 0.2s;
}
.strat-card:hover { background: var(--bg-card-hover); border-color: #353A50; }
.strat-name { font-size:0.9rem; font-weight:600; color:var(--text-primary); margin-bottom:0.2rem; }
.strat-desc { font-size:0.7rem; color:var(--text-muted); line-height:1.4; margin-bottom:0.7rem; }
.badge {
    display:inline-block; font-size:0.67rem; font-weight:700;
    padding:0.2rem 0.6rem; border-radius:20px;
    text-transform:uppercase; letter-spacing:0.07em;
}
.badge-bull { background:rgba(0,212,170,0.12); color:var(--accent-green); border:1px solid rgba(0,212,170,0.25); }
.badge-bear { background:rgba(255,107,107,0.12); color:var(--accent-red); border:1px solid rgba(255,107,107,0.25); }
.badge-neutral { background:rgba(139,144,153,0.12); color:var(--text-secondary); border:1px solid rgba(139,144,153,0.25); }

/* Section headers */
.sec-hdr {
    font-size:0.68rem; font-weight:700; color:var(--text-muted);
    text-transform:uppercase; letter-spacing:0.12em;
    padding-bottom:0.5rem;
    border-bottom:1px solid var(--border);
    margin-bottom:1rem; margin-top:1.4rem;
}

/* Feed */
.feed-wrap {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius:12px;
    padding:0.5rem 1rem;
}
.feed-row {
    display:flex; align-items:flex-start; gap:0.75rem;
    padding:0.6rem 0; border-bottom:1px solid var(--border);
}
.feed-row:last-child { border-bottom:none; }
.dot-buy  { width:8px;height:8px;border-radius:50%;background:var(--accent-green);margin-top:5px;flex-shrink:0; }
.dot-sell { width:8px;height:8px;border-radius:50%;background:var(--accent-red);margin-top:5px;flex-shrink:0; }
.feed-txt  { font-size:0.8rem; color:var(--text-primary); line-height:1.4; }
.feed-time { font-size:0.7rem; color:var(--text-muted); font-family:'JetBrains Mono',monospace; margin-top:0.12rem; }
.badge-exec { display:inline-block; font-size:0.6rem; font-weight:700; padding:0.1rem 0.45rem; border-radius:4px;
    background:rgba(0,212,170,0.1); color:var(--accent-green); border:1px solid rgba(0,212,170,0.2);
    text-transform:uppercase; letter-spacing:0.06em; margin-left:0.35rem; }
.badge-rej { display:inline-block; font-size:0.6rem; font-weight:700; padding:0.1rem 0.45rem; border-radius:4px;
    background:rgba(255,107,107,0.1); color:var(--accent-red); border:1px solid rgba(255,107,107,0.2);
    text-transform:uppercase; letter-spacing:0.06em; margin-left:0.35rem; }

/* Misc */
[data-testid="stDataFrame"] { border:1px solid var(--border) !important; border-radius:10px !important; overflow:hidden; }
[data-testid="stPlotlyChart"] > div { border:1px solid var(--border) !important; border-radius:10px !important; overflow:hidden; }
[data-testid="stExpander"] { background:var(--bg-card) !important; border:1px solid var(--border) !important; border-radius:10px !important; }
.stButton > button { background:var(--accent-purple)!important; color:white!important; border:none!important; border-radius:8px!important; font-weight:600!important; font-size:0.82rem!important; padding:0.5rem 1.25rem!important; }
.stButton > button:hover { opacity:0.85!important; }
[data-testid="stTabs"] [role="tablist"] { gap:0.1rem; border-bottom:1px solid var(--border); }
[data-testid="stTabs"] [role="tab"] { font-size:0.78rem; font-weight:600; color:var(--text-muted)!important; padding:0.5rem 0.9rem; border-radius:8px 8px 0 0; border:none!important; background:transparent!important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:var(--text-primary)!important; background:var(--bg-card)!important; border-bottom:2px solid var(--accent-purple)!important; }
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_db_engine():
    return create_engine(settings.DATABASE_URL)

db_engine = get_db_engine()

def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return now.replace(hour=9, minute=15, second=0) <= now <= now.replace(hour=15, minute=30, second=0)

def fmt_inr(val: float) -> str:
    if abs(val) >= 1e7:
        return f"Rs{val/1e7:.2f}Cr"
    if abs(val) >= 1e5:
        return f"Rs{val/1e5:.2f}L"
    return f"Rs{val:,.2f}"

def fmt_inr_sym(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{fmt_inr(val)}"

def build_strategy(name: str):
    p = STRATEGY_META[name]["params"]
    if name == "SMA Crossover":
        return SMACrossoverStrategy(**p)
    if name == "RSI Momentum":
        return RSIMomentumStrategy(**p)
    return BollingerBandsStrategy(**p)

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))

def filter_by_range(df: pd.DataFrame, range_label: str) -> pd.DataFrame:
    if df.empty:
        return df
    ts_col = "timestamp" if "timestamp" in df.columns else None
    idx = pd.to_datetime(df[ts_col] if ts_col else df.index)
    now = pd.Timestamp.now(tz=idx.dt.tz if hasattr(idx, "dt") and idx.dt.tz else None)
    cutoffs = {"Today": now - timedelta(days=1), "Weekly": now - timedelta(weeks=1), "Monthly": now - timedelta(days=30)}
    cutoff = cutoffs.get(range_label)
    if cutoff is None:
        return df
    mask = (pd.to_datetime(df[ts_col] if ts_col else df.index) >= cutoff)
    return df[mask]

def get_momentum(strategy_name: str, symbol: str) -> str:
    try:
        data = fetch_historical_data(symbol, interval="1m", period="5d")
        if data.empty or len(data) < 30:
            return "NEUTRAL"
        c = data["close"]
        if strategy_name == "SMA Crossover":
            return "BULLISH" if c.rolling(5).mean().iloc[-1] > c.rolling(20).mean().iloc[-1] else "BEARISH"
        elif strategy_name == "RSI Momentum":
            r = compute_rsi(c).iloc[-1]
            return "BULLISH" if r < 35 else ("BEARISH" if r > 65 else "NEUTRAL")
        else:
            return "BULLISH" if c.iloc[-1] < c.rolling(20).mean().iloc[-1] else "BEARISH"
    except Exception:
        return "NEUTRAL"

def kpi_card(col, label: str, value: str, delta: str, sign: int, accent: str):
    dc = "kpi-delta-pos" if sign > 0 else ("kpi-delta-neg" if sign < 0 else "kpi-delta-zero")
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-accent-bar" style="background:{accent}"></div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="{dc}">{delta}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### AgoraX")
    st.markdown("---")
    st.markdown("###### Strategy")
    selected_strategy = st.selectbox("Active Strategy", list(STRATEGY_META.keys()), label_visibility="collapsed")
    st.markdown("###### Instrument")
    selected_symbol = st.selectbox(
        "Symbol", list(STOCKS.keys()),
        format_func=lambda x: f"{x}  ·  {STOCKS[x]}",
        label_visibility="collapsed",
    )
    st.markdown("###### Time Range")
    time_range = st.radio("Range", ["Today", "Weekly", "Monthly"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    run_bt = st.button("Run Backtest", use_container_width=True)
    st.markdown("---")
    st.markdown(
        f"<div style='font-size:0.7rem;color:#555C6E;line-height:1.7'>"
        f"<b style='color:#8B9099'>Engine</b> · Paper Broker<br>"
        f"<b style='color:#8B9099'>Capital</b> · {fmt_inr(INITIAL_CAPITAL)}<br>"
        f"<b style='color:#8B9099'>Risk/Trade</b> · 2% max<br>"
        f"<b style='color:#8B9099'>Square-off</b> · 15:15 IST"
        f"</div>",
        unsafe_allow_html=True,
    )

if run_bt:
    with st.spinner(f"Simulating {selected_strategy} on {STOCKS[selected_symbol]}..."):
        data = fetch_historical_data(selected_symbol, interval="1m", period="5d")
        if not data.empty:
            eng = BacktestEngine(strategy=build_strategy(selected_strategy), historical_data=data)
            eng.run()
            st.toast(f"Backtest complete — {selected_strategy}", icon="✅")
        else:
            st.toast("Failed to fetch data. Check internet connection.", icon="⚠️")


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER BAR
# ══════════════════════════════════════════════════════════════════════════════
now_ist = datetime.now(IST)
mkt_html = ('<span class="market-open">● Market Open</span>'
            if is_market_open()
            else '<span class="market-closed">● Market Closed</span>')

st.markdown(
    f'<div class="header-bar">'
    f'<div class="header-brand">AgoraX · Quantitative Trading Workstation</div>'
    f'<div style="display:flex;align-items:center;gap:1.2rem;">'
    f'{mkt_html}'
    f'<span class="header-time">{now_ist.strftime("%d %b %Y  %H:%M:%S IST")}</span>'
    f'</div></div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA FROM DB
# ══════════════════════════════════════════════════════════════════════════════
try:
    df_runs   = pd.read_sql("SELECT * FROM backtest_runs ORDER BY id DESC", db_engine)
    df_trades = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC", db_engine)
    df_orders = pd.read_sql("SELECT * FROM orders ORDER BY timestamp DESC", db_engine)
    has_data  = not df_runs.empty
except Exception:
    df_runs = df_trades = df_orders = pd.DataFrame()
    has_data = False

latest = df_runs.iloc[0] if has_data else None


# ══════════════════════════════════════════════════════════════════════════════
#  ROW 1 — KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">Portfolio Overview</div>', unsafe_allow_html=True)
k = st.columns(6)

if has_data:
    fin  = float(latest["final_capital"] or INITIAL_CAPITAL)
    ini  = float(latest["initial_capital"])
    pnl  = fin - ini
    pnlp = (pnl / ini) * 100
    shr  = float(latest["sharpe_ratio"] or 0)
    mdd  = float(latest["max_drawdown"]  or 0)
    ttax = df_trades["total_tax"].sum()   if not df_trades.empty else 0.0
    ttrd = len(df_trades)
    nbuys= (df_trades["side"].astype(str).str.contains("BUY")).sum() if not df_trades.empty else 0
else:
    fin = ini = INITIAL_CAPITAL
    pnl = pnlp = shr = mdd = ttax = 0.0
    ttrd = nbuys = 0

kpi_card(k[0], "Portfolio Value",    fmt_inr(fin),         f"Initial: {fmt_inr(INITIAL_CAPITAL)}",  0,  "#6C63FF")
kpi_card(k[1], "Net PnL",           fmt_inr(pnl),         f"{pnlp:+.2f}%",  1 if pnl >= 0 else -1, "#00D4AA" if pnl >= 0 else "#FF6B6B")
kpi_card(k[2], "Sharpe Ratio",      f"{shr:.2f}",         "vs 7% risk-free rate", 1 if shr >= 1 else (0 if shr >= 0 else -1), "#FFB347")
kpi_card(k[3], "Max Drawdown",      f"{mdd*100:.2f}%",    "Peak-to-trough",  -1 if mdd > 0.05 else 0, "#FF6B6B")
kpi_card(k[4], "Total Trades",      str(ttrd),            f"{nbuys} buy orders", 0, "#6C63FF")
kpi_card(k[5], "Tax & Friction",    fmt_inr(ttax),        "STT · GST · SEBI", -1 if ttax > 0 else 0, "#FF6B6B")


# ══════════════════════════════════════════════════════════════════════════════
#  ROW 2 — STRATEGY MOMENTUM CARDS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="sec-hdr">Strategy Momentum · {STOCKS.get(selected_symbol, selected_symbol)}</div>',
    unsafe_allow_html=True,
)
sc = st.columns(3)
for i, (sname, smeta) in enumerate(STRATEGY_META.items()):
    mom   = get_momentum(sname, selected_symbol)
    bcls  = {"BULLISH": "badge-bull", "BEARISH": "badge-bear"}.get(mom, "badge-neutral")
    blbl  = {"BULLISH": "Bullish", "BEARISH": "Bearish"}.get(mom, "Neutral")
    arrow = {"BULLISH": "▲", "BEARISH": "▼"}.get(mom, "●")
    with sc[i]:
        st.markdown(
            f'<div class="strat-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<div class="strat-name">{smeta["icon"]} {sname}</div>'
            f'<div class="strat-desc">{smeta["description"]}</div>'
            f'</div>'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{smeta["color"]};margin-top:4px;flex-shrink:0;"></div>'
            f'</div>'
            f'<span class="badge {bcls}">{arrow} {blbl}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
t1, t2, t3, t4 = st.tabs(["📈  Price & Signals", "🧪  Tear Sheet", "📋  Activity Feed", "💸  Tax Breakdown"])


# ─── TAB 1: Price & Signals ───────────────────────────────────────────────────
with t1:
    col_chart, col_ctrl = st.columns([3, 1])
    with col_ctrl:
        chart_period   = st.selectbox("Period",   ["5d", "1mo", "3mo"], key="cp")
        chart_interval = st.selectbox("Interval", ["1m", "5m", "15m", "1d"], key="ci")
        show_ema20  = st.checkbox("EMA 20",          value=True)
        show_ema50  = st.checkbox("EMA 50",          value=True)
        show_bb     = st.checkbox("Bollinger Bands", value=False)
        show_vol    = st.checkbox("Volume Subplot",  value=True)
        show_rsi    = st.checkbox("RSI (14)",        value=True)

    with col_chart:
        cdata = fetch_historical_data(selected_symbol, interval=chart_interval, period=chart_period)
        if not cdata.empty:
            row_h  = [0.65]
            specs  = [[{"type": "candlestick"}]]
            if show_vol: row_h.append(0.15); specs.append([{"type": "bar"}])
            if show_rsi: row_h.append(0.2);  specs.append([{"type": "scatter"}])
            fig = make_subplots(rows=len(row_h), cols=1, shared_xaxes=True,
                                row_heights=row_h, vertical_spacing=0.02, specs=specs)
            fig.add_trace(go.Candlestick(
                x=cdata.index, open=cdata["open"], high=cdata["high"],
                low=cdata["low"], close=cdata["close"], name="OHLC",
                increasing_line_color="#00D4AA", decreasing_line_color="#FF6B6B",
            ), row=1, col=1)
            closes = cdata["close"]
            if show_ema20:
                fig.add_trace(go.Scatter(x=cdata.index, y=closes.ewm(span=20).mean(),
                    name="EMA 20", line=dict(color="#6C63FF", width=1.5)), row=1, col=1)
            if show_ema50:
                fig.add_trace(go.Scatter(x=cdata.index, y=closes.ewm(span=50).mean(),
                    name="EMA 50", line=dict(color="#FFB347", width=1.5)), row=1, col=1)
            if show_bb:
                sma = closes.rolling(20).mean(); std = closes.rolling(20).std()
                fig.add_trace(go.Scatter(x=cdata.index, y=sma+2*std, name="BB Upper",
                    line=dict(color="#FF6B6B", width=1, dash="dot")), row=1, col=1)
                fig.add_trace(go.Scatter(x=cdata.index, y=sma-2*std, name="BB Lower",
                    line=dict(color="#FF6B6B", width=1, dash="dot"),
                    fill="tonexty", fillcolor="rgba(255,107,107,0.04)"), row=1, col=1)

            # Trade markers from DB
            if not df_trades.empty:
                sym_t = df_trades[df_trades["symbol"] == selected_symbol].copy()
                sym_t["timestamp"] = pd.to_datetime(sym_t["timestamp"])
                buys  = sym_t[sym_t["side"].astype(str).str.contains("BUY")]
                sells = sym_t[sym_t["side"].astype(str).str.contains("SELL")]
                if not buys.empty:
                    fig.add_trace(go.Scatter(x=buys["timestamp"], y=buys["price"], mode="markers",
                        name="Buy", marker=dict(color="#00D4AA", symbol="triangle-up", size=11)), row=1, col=1)
                if not sells.empty:
                    fig.add_trace(go.Scatter(x=sells["timestamp"], y=sells["price"], mode="markers",
                        name="Sell", marker=dict(color="#FF6B6B", symbol="triangle-down", size=11)), row=1, col=1)

            cur_row = 2
            if show_vol and "volume" in cdata.columns:
                vcol = ["#00D4AA" if cdata["close"].iloc[i] >= cdata["open"].iloc[i]
                        else "#FF6B6B" for i in range(len(cdata))]
                fig.add_trace(go.Bar(x=cdata.index, y=cdata["volume"],
                    name="Volume", marker_color=vcol, opacity=0.55), row=cur_row, col=1)
                cur_row += 1
            if show_rsi:
                rsi_s = compute_rsi(closes)
                fig.add_trace(go.Scatter(x=cdata.index, y=rsi_s, name="RSI 14",
                    line=dict(color="#6C63FF", width=1.5)), row=cur_row, col=1)
                fig.add_hline(y=70, line=dict(color="#FF6B6B", width=1, dash="dot"), row=cur_row, col=1)
                fig.add_hline(y=30, line=dict(color="#00D4AA", width=1, dash="dot"), row=cur_row, col=1)
                fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,107,107,0.04)", line_width=0, row=cur_row, col=1)
                fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,212,170,0.04)",   line_width=0, row=cur_row, col=1)

            fig.update_layout(
                height=550 + (120 if show_vol else 0) + (120 if show_rsi else 0),
                paper_bgcolor="#1A1E2E", plot_bgcolor="#1A1E2E",
                font=dict(family="Inter", color="#8B9099", size=11),
                legend=dict(orientation="h", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_rangeslider_visible=False,
                xaxis=dict(gridcolor="#252A3A", zeroline=False),
                yaxis=dict(gridcolor="#252A3A", zeroline=False, title="Price (Rs)"),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No chart data. Run a backtest or check your connection.")


# ─── TAB 2: Strategy Tear Sheet ───────────────────────────────────────────────
with t2:
    if not has_data:
        st.info("No backtest data yet. Use the sidebar to run a backtest first.")
    else:
        ft = filter_by_range(df_trades.copy(), time_range) if not df_trades.empty else pd.DataFrame()
        buys_mask  = ft["side"].astype(str).str.contains("BUY")  if not ft.empty else pd.Series([], dtype=bool)
        sells_mask = ft["side"].astype(str).str.contains("SELL") if not ft.empty else pd.Series([], dtype=bool)
        buy_val  = (ft[buys_mask]["price"]  * ft[buys_mask]["quantity"]).sum()  if not ft.empty else 0
        sell_val = (ft[sells_mask]["price"] * ft[sells_mask]["quantity"]).sum() if not ft.empty else 0
        gross    = sell_val - buy_val
        friction = ft["total_tax"].sum() if not ft.empty else 0

        st.markdown('<div class="sec-hdr">Performance Summary</div>', unsafe_allow_html=True)
        pc = st.columns(5)

        def mini(col, lbl, val):
            col.markdown(
                f'<div class="kpi-card" style="padding:0.8rem 1rem;">'
                f'<div class="kpi-label">{lbl}</div>'
                f'<div class="kpi-value" style="font-size:1rem;">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        mini(pc[0], "Strategy",           latest["strategy_name"])
        mini(pc[1], "Gross PnL",          fmt_inr(gross))
        mini(pc[2], "Net PnL (after tax)", fmt_inr(gross - friction))
        mini(pc[3], "Trades in Range",    str(len(ft)))
        mini(pc[4], "Period",             time_range)

        st.markdown('<div class="sec-hdr">Equity Curve & Drawdown</div>', unsafe_allow_html=True)
        try:
            eq_data = pd.read_sql("SELECT * FROM backtest_runs ORDER BY start_time", db_engine)
            if not eq_data.empty and eq_data["final_capital"].notna().any():
                eq = eq_data["final_capital"].fillna(method="ffill")
                rolling_max = eq.cummax()
                dd = (eq - rolling_max) / rolling_max * 100

                efig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                     row_heights=[0.65, 0.35], vertical_spacing=0.04)
                efig.add_trace(go.Scatter(
                    x=eq_data["start_time"], y=eq, name="Equity",
                    line=dict(color="#6C63FF", width=2),
                    fill="tozeroy", fillcolor="rgba(108,99,255,0.07)"), row=1, col=1)
                efig.add_trace(go.Scatter(
                    x=eq_data["start_time"], y=dd, name="Drawdown %",
                    line=dict(color="#FF6B6B", width=1.5),
                    fill="tozeroy", fillcolor="rgba(255,107,107,0.08)"), row=2, col=1)
                efig.update_layout(
                    height=360, paper_bgcolor="#1A1E2E", plot_bgcolor="#1A1E2E",
                    font=dict(family="Inter", color="#8B9099", size=11),
                    legend=dict(orientation="h", y=1.03, bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified",
                    xaxis=dict(gridcolor="#252A3A"), yaxis=dict(gridcolor="#252A3A", title="Capital (Rs)"),
                    xaxis2=dict(gridcolor="#252A3A"), yaxis2=dict(gridcolor="#252A3A", title="Drawdown %"),
                )
                st.plotly_chart(efig, use_container_width=True, config={"displayModeBar": False})
        except Exception as e:
            st.caption(f"Equity chart unavailable: {e}")

        with st.expander("View Detailed Trade Breakdown"):
            if not ft.empty:
                show_cols = ["symbol", "side", "quantity", "price", "timestamp",
                             "brokerage", "stt", "gst", "total_tax"]
                show_cols = [c for c in show_cols if c in ft.columns]
                disp = ft[show_cols].copy()
                disp.columns = [c.replace("_", " ").title() for c in disp.columns]
                st.dataframe(disp, use_container_width=True, hide_index=True)
            else:
                st.caption("No trade data for this time range.")


# ─── TAB 3: Activity Feed ─────────────────────────────────────────────────────
with t3:
    st.markdown('<div class="sec-hdr">Trade Execution Log</div>', unsafe_allow_html=True)
    fl, fr = st.columns([2, 1])

    with fl:
        ford = filter_by_range(df_orders.copy(), time_range) if not df_orders.empty else pd.DataFrame()
        if ford.empty:
            st.markdown(
                '<div style="padding:2rem;text-align:center;color:#555C6E;font-size:0.9rem;">'
                'No orders found for this time range.<br>Run a backtest to generate activity.</div>',
                unsafe_allow_html=True,
            )
        else:
            rows_html = ""
            for _, row in ford.head(40).iterrows():
                side   = str(row.get("side", "")).upper()
                status = str(row.get("status", "")).upper()
                sym    = str(row.get("symbol", "N/A"))
                qty    = int(row.get("quantity", 0))
                price  = row.get("price") or 0
                ts     = str(row.get("timestamp", ""))[:16]
                otype  = str(row.get("order_type", "MARKET"))
                dot    = "dot-buy"  if "BUY"  in side else "dot-sell"
                act    = "Buy Order" if "BUY" in side else "Sell Order"
                plbl   = f"@ Rs{price:,.2f}" if price else "@ Market"
                if "EXECUTED" in status:
                    sbadge = '<span class="badge-exec">Executed</span>'
                elif "REJECTED" in status:
                    sbadge = '<span class="badge-rej">Rejected</span>'
                elif "CANCELLED" in status:
                    sbadge = '<span class="badge-rej">Cancelled</span>'
                else:
                    sbadge = '<span class="badge-rej">Pending</span>'
                rows_html += (
                    f'<div class="feed-row">'
                    f'<div class="{dot}"></div>'
                    f'<div>'
                    f'<div class="feed-txt"><b>{act}</b> · {qty} x <b>{sym}</b> {plbl} · {otype} {sbadge}</div>'
                    f'<div class="feed-time">{ts}</div>'
                    f'</div>'
                    f'</div>'
                )
            st.markdown(f'<div class="feed-wrap">{rows_html}</div>', unsafe_allow_html=True)

    with fr:
        st.markdown('<div class="sec-hdr">Quick Stats</div>', unsafe_allow_html=True)
        if not ford.empty:
            sv    = ford["status"].astype(str).str.upper().value_counts()
            exc   = int(sv.get("EXECUTED", 0))
            rej   = int(sv.get("REJECTED",  0))
            can   = int(sv.get("CANCELLED", 0))
            tot   = len(ford)
            rate  = exc / tot * 100 if tot else 0
            st.markdown(
                f'<div style="display:flex;flex-direction:column;gap:0.6rem;">'
                f'<div class="kpi-card" style="padding:0.75rem 1rem;">'
                f'<div class="kpi-label">Fill Rate</div><div class="kpi-value" style="font-size:1.3rem;">{rate:.1f}%</div></div>'
                f'<div class="kpi-card" style="padding:0.75rem 1rem;">'
                f'<div class="kpi-label">Executed</div><div class="kpi-value" style="font-size:1.3rem;color:#00D4AA">{exc}</div></div>'
                f'<div class="kpi-card" style="padding:0.75rem 1rem;">'
                f'<div class="kpi-label">Rejected</div><div class="kpi-value" style="font-size:1.3rem;color:#FF6B6B">{rej}</div></div>'
                f'<div class="kpi-card" style="padding:0.75rem 1rem;">'
                f'<div class="kpi-label">Cancelled</div><div class="kpi-value" style="font-size:1.3rem;color:#8B9099">{can}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No order data available.")


# ─── TAB 4: Tax Breakdown ─────────────────────────────────────────────────────
with t4:
    st.markdown('<div class="sec-hdr">Indian Regulatory & Tax Impact on Strategy PnL</div>', unsafe_allow_html=True)
    ftx = filter_by_range(df_trades.copy(), time_range) if not df_trades.empty else pd.DataFrame()
    if not ftx.empty:
        TAX_COLS = ["brokerage", "stt", "exchange_charges", "sebi_charges", "gst", "stamp_duty", "total_tax"]
        LABELS   = {"brokerage":"Brokerage","stt":"STT","exchange_charges":"Exchange Fee",
                    "sebi_charges":"SEBI Charges","gst":"GST (18%)","stamp_duty":"Stamp Duty","total_tax":"Total Friction"}
        totals = {c: ftx[c].sum() for c in TAX_COLS if c in ftx.columns}
        tc = st.columns(len(totals))
        for i, (cn, v) in enumerate(totals.items()):
            tc[i].markdown(
                f'<div class="kpi-card" style="padding:0.8rem 1rem;">'
                f'<div class="kpi-label">{LABELS.get(cn,cn)}</div>'
                f'<div class="kpi-value" style="font-size:1rem;color:#FF6B6B">Rs{v:,.2f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        dl = [LABELS.get(k,k) for k in TAX_COLS[:-1] if k in totals and totals[k] > 0]
        dv = [totals[k]       for k in TAX_COLS[:-1] if k in totals and totals[k] > 0]
        if dv:
            tl, tr = st.columns([1, 2])
            with tl:
                dfig = go.Figure(go.Pie(
                    labels=dl, values=dv, hole=0.6,
                    marker=dict(colors=["#6C63FF","#00D4AA","#FFB347","#FF6B6B","#4ECDC4","#A8DADC"]),
                    textinfo="percent", textfont=dict(size=11, color="white"),
                    hovertemplate="%{label}: Rs%{value:,.2f}<extra></extra>",
                ))
                dfig.update_layout(
                    height=270, paper_bgcolor="#1A1E2E", plot_bgcolor="#1A1E2E",
                    margin=dict(l=0,r=0,t=20,b=0),
                    font=dict(family="Inter", color="#8B9099", size=11),
                    legend=dict(orientation="v", font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    annotations=[dict(text="<b>Costs</b>", x=0.5, y=0.5,
                                      font_size=13, font_color="#E8EAED", showarrow=False)],
                )
                st.plotly_chart(dfig, use_container_width=True, config={"displayModeBar": False})
            with tr:
                with st.expander("Per-Trade Tax Detail", expanded=True):
                    show = [c for c in ["symbol","side","quantity","price"] + TAX_COLS if c in ftx.columns]
                    d2 = ftx[show].copy()
                    d2.columns = [c.replace("_"," ").title() for c in d2.columns]
                    st.dataframe(d2.head(30), use_container_width=True, hide_index=True)
    else:
        st.info("No trade data available for the selected time range.")
