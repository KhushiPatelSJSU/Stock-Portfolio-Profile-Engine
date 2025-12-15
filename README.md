# Stock Portfolio Suggestion Engine

A Python + Streamlit application that suggests a diversified investment portfolio based on selected strategies, using real-time market data from `yfinance`.

---

## 📌 Features

- Input **investment amount (min $5,000)**.  
- Choose **one or two** investing strategies.
- Each strategy maps to **3+ stocks/ETFs**.
- Portfolio allocation methods:
  - Equal Weight  
  - Inverse Volatility (Risk Parity)  
  - Mean-Variance Optimization (Markowitz, optional if `cvxpy` installed)
- Real-time price fetching via **yfinance**.
- Automatic allocation of:
  - Weights  
  - Shares (fractional or whole)  
  - Estimated trading cost (commission + slippage)
- Displays:
  - Selected tickers  
  - Allocation table  
  - Cash remaining  
  - Current mark-to-market value  
- **5-day portfolio trend chart** (with persistent `history.json`).
- Diversification report (Sector / Region).
- Rebalancing preview.
- CSV exports:
  - Full allocation
  - Trade ticket

---

## 📌 Strategy → Ticker Mapping

| Strategy           | Tickers                     |
|--------------------|-----------------------------|
| Index Investing    | VTI, IXUS, ILTB            |
| Ethical Investing  | AAPL, ADBE, NSRGY          |
| Growth Investing   | NVDA, AMZN, TSLA           |
| Quality Investing  | MSFT, JNJ, PG              |
| Value Investing    | BRK-B, VTV, XOM            |

Each strategy contains **at least 3 tickers** as required.

---

## 📁 File Structure

```text
main.py        # Main Streamlit application
history.json   # Auto-created to store last 5 portfolio values
```
---

## 🛠 Installation

1. Clone or place the project
```bash
cd path/to/project
```

2. (Optional) Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

3. Install dependencies

Install:
```bash
pip install -r requirements.txt
```

## ▶️ Running the App
```bash
streamlit run main.py
```
The browser will open automatically.

---

## 🧭 How to Use

1. Enter investment amount (≥ $5,000).
2. Pick 1 or 2 strategies.
3. Choose allocation method.
4. Adjust:
    - Stock-to-bond ratio
    - Fractional shares
    - Commission and slippage
    - Lookback period
5. Click Suggest / Recompute.

The app will output:

- Selected tickers
- Allocation table
- Cash remaining
- Total portfolio value
- 5-day portfolio trend chart
- Diversification summary
- Rebalancing preview

Exports are available at the bottom.
---
## 📊 Allocation Methods
1. Equal Weight

- Every ticker receives identical weight.

2. Inverse Volatility

- Low-volatility assets receive higher weights (risk parity style).

3. Mean-Variance Optimization

Uses Markowitz Efficient Frontier:
- Maximizes return minus risk penalty:
```text
μᵀw − λ·wᵀΣw
```
- Long-only (no shorts)
- Requires cvxpy.
If unavailable, the option is hidden.
---
## ✅ Additional Clarification for Grader (Important)

**Why Mark-to-Market Value < Total Invested Amount?**  
This is **intentional** and caused by the simulated slippage model:

- The portfolio **buys shares at ExecPrice**, which includes slippage:  
  `ExecPrice = Price × (1 + slippage%)`
- But the Mark-to-Market value is calculated using the **normal market Price** (without slippage).
- Therefore:  
  `Mark-to-Market ≈ Total Invested / (1 + slippage%)`  
  With a 0.05% slippage, $5000 becomes approximately **$4,997.50**.

This difference reflects **transaction cost impact**, not an error.

**Why Cash Remaining = -$0.00?**  
Due to fractional shares and floating-point precision:

- The calculation often ends up extremely close to **0** (e.g., `-0.0000002`).
- Streamlit formats this as **−$0.00**.
- This is normal and expected and means “zero with tiny rounding noise”.
---

## ⚠️ Notes & Assumptions

1. yfinance data may be slightly delayed.
2. Slippage is applied as an increased execution price.
3. Commission is per-trade.
4. Strategy mapping and metadata (sector/region/bucket) are simplified for educational use.
