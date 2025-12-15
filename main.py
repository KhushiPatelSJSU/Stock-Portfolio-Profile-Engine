# main.py — CMPE 285 • Stock Portfolio Suggestion Engine (yfinance, advanced)

import os
import io
import json
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st

# Try to import cvxpy for mean-variance optimization (optional)
try:
    import cvxpy as cp
    HAS_CVXPY = True
except Exception:
    HAS_CVXPY = False

# -----------------------------
# Config
# -----------------------------
MIN_INVEST_USD = 5000
HISTORY_FILE = "history.json"   # stores last 5 dates of total portfolio value

# Strategy → tickers (≥ 3 each)
STRATEGY_MAP: Dict[str, List[str]] = {
    "Index Investing":   ["VTI", "IXUS", "ILTB"],
    "Ethical Investing": ["AAPL", "ADBE", "NSRGY"],
    "Growth Investing":  ["NVDA", "AMZN", "TSLA"],
    "Quality Investing": ["MSFT", "JNJ", "PG"],
    "Value Investing":   ["BRK-B", "VTV", "XOM"],
}

# Simple metadata for sector/region/bucket (ETF buckets are broad)
META = {
    # ETFs
    "VTI":  {"sector": "Broad Market", "region": "US", "bucket": "Equity"},
    "IXUS": {"sector": "Broad Market", "region": "International ex-US", "bucket": "Equity"},
    "ILTB": {"sector": "Bond", "region": "US", "bucket": "Bond"},
    "VTV":  {"sector": "Value", "region": "US", "bucket": "Equity"},
    # Large caps
    "AAPL": {"sector": "Technology", "region": "US", "bucket": "Equity"},
    "ADBE": {"sector": "Technology", "region": "US", "bucket": "Equity"},
    "NSRGY":{"sector": "Consumer Staples", "region": "International", "bucket": "Equity"},
    "NVDA": {"sector": "Technology", "region": "US", "bucket": "Equity"},
    "AMZN": {"sector": "Consumer Discretionary", "region": "US", "bucket": "Equity"},
    "TSLA": {"sector": "Consumer Discretionary", "region": "US", "bucket": "Equity"},
    "MSFT": {"sector": "Technology", "region": "US", "bucket": "Equity"},
    "JNJ":  {"sector": "Health Care", "region": "US", "bucket": "Equity"},
    "PG":   {"sector": "Consumer Staples", "region": "US", "bucket": "Equity"},
    "BRK-B":{"sector": "Financials", "region": "US", "bucket": "Equity"},
    "XOM":  {"sector": "Energy", "region": "US", "bucket": "Equity"},
}

# -----------------------------
# Price & history helpers (yfinance)
# -----------------------------
def get_price(ticker: str) -> float:
    """Best-effort latest price via yfinance (fast_info, then last close)."""
    t = yf.Ticker(ticker)
    # fast path
    try:
        info = t.fast_info
        p = float(info.get("last_price"))
        if p and p > 0:
            return p
    except Exception:
        pass
    # fallback: last close
    hist = t.history(period="5d")
    if not hist.empty:
        return float(hist["Close"].iloc[-1])
    raise RuntimeError(f"No price data for {ticker}")

def get_hist_close_prices(tickers: List[str], days: int = 252) -> pd.DataFrame:
    """
    Historical closes for the past ~days calendar days (default ~1y trading days).
    Handles single/multiple tickers.
    """
    data = yf.download(tickers, period=f"{days}d", auto_adjust=False, progress=False)
    if isinstance(data, pd.DataFrame) and "Close" in data.columns:
        closes = data["Close"]
    else:
        closes = pd.DataFrame({tickers[0]: data["Close"]})
    # Normalize Berkshire column naming
    if "BRK.B" in closes.columns:
        closes = closes.rename(columns={"BRK.B": "BRK-B"})
    return closes.dropna(how="all")

# -----------------------------
# Persistence for 5-day total value history
# -----------------------------
def load_history() -> Dict[str, float]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(hist: Dict[str, float]) -> None:
    # keep only last 5 by date (sorted)
    items = sorted(hist.items(), key=lambda kv: kv[0])
    trimmed = dict(items[-5:])
    with open(HISTORY_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def upsert_today_value(total_value: float) -> None:
    hist = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    hist[today] = float(total_value)
    save_history(hist)

# -----------------------------
# Allocation helpers
# -----------------------------
def build_universe(selected_strategies: List[str]) -> List[str]:
    """De-duplicated list of tickers in selection order."""
    seen, out = set(), []
    for s in selected_strategies:
        for t in STRATEGY_MAP[s]:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out

def classify_ticker(t: str) -> str:
    return META.get(t, {}).get("bucket", "Equity")

def _prices_for(tickers: List[str]) -> Dict[str, float]:
    return {t: get_price(t) for t in tickers}

def weights_equal(tickers: List[str]) -> pd.Series:
    n = len(tickers)
    if n == 0:
        return pd.Series(dtype=float)
    return pd.Series(1.0 / n, index=tickers)

def weights_inverse_vol(tickers: List[str], lookback_days: int = 126) -> pd.Series:
    closes = get_hist_close_prices(tickers, days=lookback_days + 10).dropna()
    rets = closes.pct_change().dropna()
    vol = rets.std()
    inv_vol = 1.0 / vol.replace(0, np.nan)
    w = inv_vol / inv_vol.sum()
    return w.fillna(0.0)

def weights_mean_variance(tickers: List[str], target_vol: float = None, risk_aversion: float = 5.0,
                          lookback_days: int = 252) -> pd.Series:
    """Classic mean-variance (max Sharpe via risk_aversion) using cvxpy if available."""
    if not HAS_CVXPY:
        return weights_equal(tickers)
    closes = get_hist_close_prices(tickers, days=lookback_days + 10).dropna()
    rets = closes.pct_change().dropna()
    mu = rets.mean().values  # expected daily returns
    Sigma = np.cov(rets.T)   # covariance

    n = len(tickers)
    w = cp.Variable(n)
    # Objective: maximize mu^T w - lambda * w^T Sigma w
    lam = risk_aversion
    objective = cp.Maximize(mu @ w - lam * cp.quad_form(w, Sigma))
    constraints = [cp.sum(w) == 1, w >= 0]  # long-only, fully invested
    if target_vol is not None:
        constraints.append(cp.quad_form(w, Sigma) <= target_vol ** 2)
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.SCS, verbose=False)
        sol = np.maximum(w.value, 0.0)
        if sol.sum() == 0:
            return weights_equal(tickers)
        sol = sol / sol.sum()
        return pd.Series(sol, index=tickers)
    except Exception:
        return weights_equal(tickers)

def blend_stock_bond(weights: pd.Series, tickers: List[str], stock_ratio: float) -> pd.Series:
    """Scale weights to match a stock/bond split based on simple Equity/Bond classification."""
    buckets = pd.Series({t: classify_ticker(t) for t in tickers})
    stock_mask = (buckets == "Equity").astype(float)
    bond_mask  = (buckets == "Bond").astype(float)
    w_stock = (weights * stock_mask)
    w_bond  = (weights * bond_mask)
    stock_sum = w_stock.sum()
    bond_sum  = w_bond.sum()
    if stock_sum > 0:
        w_stock = w_stock * (stock_ratio / stock_sum)
    if bond_sum > 0:
        w_bond = w_bond * ((1 - stock_ratio) / bond_sum)
    out = w_stock.add(w_bond, fill_value=0.0)
    if out.sum() > 0:
        out = out / out.sum()
    return out

def allocate_shares(amount_usd: float,
                    tickers: List[str],
                    weights: pd.Series,
                    prices: Dict[str, float],
                    fractional: bool,
                    commission_per_trade: float,
                    slippage_pct: float) -> Tuple[pd.DataFrame, float]:
    """
    Produce allocation with shares (fractional or whole), include estimated
    transaction costs: commission + slippage (as price * (1+slip)).
    Returns (df, remaining_cash).
    """
    rows = []
    invested = 0.0
    slip_mult = 1.0 + slippage_pct / 100.0
    for t in tickers:
        w = float(weights.get(t, 0.0))
        target_dollars = max(0.0, amount_usd * w)
        px = float(prices[t]) * slip_mult  # assume we pay slippage on entry
        if fractional:
            shares = round(target_dollars / px, 6)  # high precision fractional
        else:
            shares = int(target_dollars // px)
        cost = shares * px + (commission_per_trade if shares > 0 else 0.0)
        invested += cost
        rows.append({"Ticker": t, "Price": prices[t], "ExecPrice": px, "Weight": w,
                     "Shares": shares, "EstCostUSD": cost})
    df = pd.DataFrame(rows)
    cash_left = float(amount_usd - invested)
    return df, cash_left

def reprice_value(df_alloc: pd.DataFrame) -> float:
    """Reprice portfolio ignoring slippage/commissions (mark-to-market)."""
    total = 0.0
    for _, row in df_alloc.iterrows():
        px = get_price(str(row["Ticker"]))
        total += float(row["Shares"]) * px
    return float(total)

def compute_5day_series(df_alloc: pd.DataFrame) -> pd.Series:
    """Compute portfolio value over last 5 trading days using historical closes."""
    if df_alloc.empty:
        return pd.Series(dtype=float)
    tickers = list(df_alloc["Ticker"].astype(str).values)
    closes = get_hist_close_prices(tickers, days=30)

    # Align columns to held tickers
    shares = df_alloc.set_index("Ticker")["Shares"].to_dict()
    for c in list(closes.columns):
        if c not in shares:
            closes = closes.drop(columns=[c])
    for t in shares:
        if t not in closes.columns:
            closes[t] = 0.0
    closes = closes[sorted(closes.columns)]

    daily_vals = (closes * pd.Series(shares).reindex(closes.columns).fillna(0)).sum(axis=1)
    daily_vals = daily_vals.dropna().tail(5)
    daily_vals.index = daily_vals.index.strftime("%Y-%m-%d")
    return daily_vals

def diversification_report(df_alloc: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (sector_df, region_df) breakdowns by market value weights."""
    if df_alloc.empty:
        return pd.DataFrame(), pd.DataFrame()
    tickers = df_alloc["Ticker"].tolist()
    prices = {t: get_price(t) for t in tickers}
    mv = pd.Series({t: prices[t] * float(sh) for t, sh in zip(df_alloc["Ticker"], df_alloc["Shares"])})
    w = mv / mv.sum()

    meta = pd.DataFrame(
        {t: {"sector": META.get(t, {}).get("sector", "Unknown"),
             "region": META.get(t, {}).get("region", "Unknown")}
         for t in tickers}
    ).T
    meta["weight"] = w

    sector = meta.groupby("sector")["weight"].sum().sort_values(ascending=False)
    region = meta.groupby("region")["weight"].sum().sort_values(ascending=False)

    sector_df = sector.reset_index().rename(columns={"weight": "Weight"})
    region_df = region.reset_index().rename(columns={"weight": "Weight"})
    sector_df["WeightPct"] = (sector_df["Weight"] * 100).round(2)
    region_df["WeightPct"] = (region_df["Weight"] * 100).round(2)
    return sector_df, region_df

def trade_ticket_from_allocation(df_alloc: pd.DataFrame) -> pd.DataFrame:
    """Simple buy ticket assuming fresh portfolio build."""
    tt = df_alloc.copy()
    tt = tt.loc[tt["Shares"] > 0, ["Ticker", "Shares", "ExecPrice", "EstCostUSD"]].reset_index(drop=True)
    tt["Side"] = "BUY"
    cols = ["Side", "Ticker", "Shares", "ExecPrice", "EstCostUSD"]
    return tt[cols]

# -----------------------------
# UI (Streamlit)
# -----------------------------
st.set_page_config(page_title="CMPE 285 – Portfolio Suggestion Engine", layout="wide")
st.title("📈 CMPE 285 – Stock Portfolio Suggestion Engine (yfinance)")

with st.sidebar:
    st.header("Inputs")
    amount = st.number_input(
        "Dollar amount to invest (USD)", min_value=MIN_INVEST_USD, step=500, value=MIN_INVEST_USD
    )
    strategies = st.multiselect(
        "Pick one or two strategies", options=list(STRATEGY_MAP.keys()), max_selections=2
    )

    st.markdown("### Allocation Method")
    method = st.selectbox("Method", ["Equal-Weight", "Inverse-Volatility (Risk Parity)"] + (["Mean-Variance (cvxpy)"] if HAS_CVXPY else []))

    stock_bond = st.slider("Target stock ratio (for Equity vs Bond buckets)", min_value=0, max_value=100, value=80, step=5)
    fractional = st.checkbox("Allow fractional shares", value=True)
    commission = st.number_input("Commission per trade ($)", min_value=0.0, value=0.0, step=0.5)
    slippage = st.number_input("Slippage (%)", min_value=0.0, value=0.05, step=0.05, help="Applied to execution price on buys")

    lookback = st.slider("Lookback days for risk/optimization", min_value=60, max_value=365, value=252, step=15)
    risk_aversion = st.slider("Mean-variance risk aversion (λ, higher = more conservative)", min_value=1.0, max_value=20.0, value=5.0, step=0.5) if ("Mean-Variance (cvxpy)" in method) else None

    run = st.button("Suggest / Recompute")

if "has_run" not in st.session_state:
    st.session_state["has_run"] = False

if run:
    st.session_state["has_run"] = True

st.markdown("---")

if not st.session_state["has_run"]:
    st.info("⬅️ Enter inputs, then click **Suggest / Recompute**.")
    st.stop()

if len(strategies) == 0:
    st.warning("Please select at least one strategy.")
    st.stop()

# Build universe & compute weights
universe = build_universe(strategies)
prices = _prices_for(universe)

if method.startswith("Equal"):
    w = weights_equal(universe)
elif method.startswith("Inverse"):
    w = weights_inverse_vol(universe, lookback_days=lookback)
else:  # Mean-Variance
    w = weights_mean_variance(universe, risk_aversion=risk_aversion, lookback_days=lookback)

# Blend to desired stock/bond split
w = blend_stock_bond(w, universe, stock_ratio=stock_bond / 100.0)
w = (w / w.sum()) if w.sum() > 0 else weights_equal(universe)

# Allocate (with tx costs + slippage)
alloc_df, cash_left = allocate_shares(
    amount_usd=amount,
    tickers=universe,
    weights=w,
    prices=prices,
    fractional=fractional,
    commission_per_trade=commission,
    slippage_pct=slippage,
)

# Filter zero-share rows for display clarity
alloc_shown = alloc_df[alloc_df["Shares"] > 0].copy()

# Current value (mark-to-market)
current_total = reprice_value(alloc_df)

# Persist & 5-day chart
series5 = compute_5day_series(alloc_df)
upsert_today_value(current_total)
file_hist = load_history()
for d, v in file_hist.items():
    series5.loc[d] = v
series5 = series5.sort_index().tail(5)

# -----------------------------
# Display
# -----------------------------
st.subheader("Selected Strategies & Mapped Tickers")
st.write({s: STRATEGY_MAP[s] for s in strategies})

c1, c2, c3 = st.columns([3, 1.5, 1.5])
with c1:
    st.subheader("Allocation by Ticker")
    display_cols = ["Ticker", "Weight", "Price", "ExecPrice", "Shares", "EstCostUSD"]
    df_show = alloc_shown.copy()
    df_show["Weight"] = (df_show["Weight"] * 100).round(2)
    df_show["EstCostUSD"] = df_show["EstCostUSD"].round(2)
    st.dataframe(df_show[display_cols], use_container_width=True)
with c2:
    st.metric("Cash Remaining (USD)", f"${cash_left:,.2f}")
with c3:
    st.metric("Mark-to-Market Value (USD)", f"${current_total:,.2f}")

st.subheader("5-Day Portfolio Trend")
st.line_chart(series5.rename("Portfolio USD"))

# Diversification
st.subheader("Diversification Checks")
sector_df, region_df = diversification_report(alloc_df)
colA, colB = st.columns(2)
with colA:
    st.markdown("**By Sector**")
    if not sector_df.empty:
        st.dataframe(sector_df, use_container_width=True)
    else:
        st.write("—")
with colB:
    st.markdown("**By Region**")
    if not region_df.empty:
        st.dataframe(region_df, use_container_width=True)
    else:
        st.write("—")

# Rebalancing preview to current target weights (from current prices)
st.subheader("Rebalancing Preview")
# Current weights from MV
mv_prices = {t: get_price(t) for t in universe}
mv_values = pd.Series({t: float(sh)*mv_prices[t] for t, sh in zip(alloc_df["Ticker"], alloc_df["Shares"])})
total_mv = mv_values.sum() if mv_values.sum() > 0 else 1.0
curr_w = mv_values / total_mv
target_w = w
diff = (target_w - curr_w).sort_values(ascending=False)
rb_df = pd.DataFrame({"CurrentW": curr_w, "TargetW": target_w, "Diff": diff}).fillna(0.0)
rb_df["CurrentW%"] = (rb_df["CurrentW"]*100).round(2)
rb_df["TargetW%"] = (rb_df["TargetW"]*100).round(2)
rb_df["Diff%"] = (rb_df["Diff"]*100).round(2)
st.dataframe(rb_df[["CurrentW%", "TargetW%", "Diff%"]].sort_values("Diff%", ascending=False), use_container_width=True)

# Export buttons
st.subheader("Exports")
ticket = trade_ticket_from_allocation(alloc_df)
alloc_csv = alloc_df.to_csv(index=False)
ticket_csv = ticket.to_csv(index=False)

st.download_button("Download Allocation CSV", data=alloc_csv, file_name="allocation.csv", mime="text/csv")
st.download_button("Download Trade Ticket CSV", data=ticket_csv, file_name="trade_ticket.csv", mime="text/csv")

# Notes
with st.expander("Notes & Assumptions"):
    st.markdown(
        """
- **Price source**: yfinance only; latest may reflect last close (data can be delayed).
- **Transaction costs**: Commission is per trade when shares > 0. Slippage increases execution price by %.
- **Risk methods**:
  - *Equal-Weight*: same weight for each ticker (then scaled to stock/bond split).
  - *Inverse-Volatility*: weights ∝ 1/σ using lookback window.
  - *Mean-Variance*: requires `cvxpy`; maximizes μᵀw − λ·wᵀΣw, long-only, sum(w)=1.
- **Rebalancing**: Table shows diff between current MV weights and the target weights you chose.
- **Diversification**: Sector/Region tags are approximate for demo purposes.
- **History**: `history.json` stores last five dates of total portfolio value.
        """
    )

st.success("Done. Adjust inputs in the sidebar to iterate.")
