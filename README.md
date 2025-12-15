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

## Why Mark-to-Market Value < Total Invested Amount?

This is **intentional** and caused by the simulated slippage model:

- The portfolio **buys shares at ExecPrice**, which includes slippage:  
  `ExecPrice = Price × (1 + slippage%)`
- But the Mark-to-Market value is calculated using the **normal market Price** (without slippage).
- Therefore:  
  `Mark-to-Market ≈ Total Invested / (1 + slippage%)`  
  With a 0.05% slippage, $5000 becomes approximately **$4,997.50**.

This difference reflects **transaction cost impact**, not an error.

## Why Cash Remaining = -$0.00?

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

---

# ✅ Test Cases

For all tests, run the app online at:

**🔗 Live App:** [https://stock-portfolio-profile-engine.streamlit.app/](https://stock-portfolio-profile-engine.streamlit.app/)

Or locally:

```bash
streamlit run main.py
```

Then follow the steps in each test case.

---

## 🧪 Test 1 – Single Strategy, Equal Weight, Fractional ON

**Input**

* Amount: **$5,000**
* Strategy: **Index Investing**
* Method: **Equal-Weight**
* Stock/Bond: **80%**
* Fractional shares: **ON**
* Commission: **$0**
* Slippage: **0.05%**

**Expected Output**

* Selected tickers: **VTI, IXUS, ILTB**
* Allocation table shows **3 rows**
* Cash Remaining ≈ **$0.00**
* Mark-to-Market equals sum of `Shares × Price`
* Trend chart, diversification, and rebalancing sections display normally

---

## 🧪 Test 2 – Two Strategies Combined, Equal Weight

**Input**

* Amount: **$10,000**
* Strategies: **Index Investing + Growth Investing**
* Method: **Equal-Weight**
* Fractional shares: **ON**

**Expected Output**

* Universe contains **6 tickers**
  (`VTI, IXUS, ILTB, NVDA, AMZN, TSLA`)
* Weights are roughly even (after stock/bond adjustment)
* Diversification shows both **Tech** and **Broad Market** exposure

---

## 🧪 Test 3 – Inverse Volatility (Risk Parity)

**Input**

* Amount: any value ≥ **$5,000**
* Strategy: e.g. **Quality Investing**
* Method: **Inverse-Volatility**
* Fractional shares: **ON**

**Expected Output**

* App runs without errors
* Weights differ noticeably from Equal-Weight (low-volatility tickers get higher weight)
* Allocation, diversification, and rebalancing render correctly

---

## 🧪 Test 4 – Mean-Variance Optimization (If cvxpy Installed)

**Input**

* Amount: **$10,000**
* Strategy: **Growth Investing**
* Method: **Mean-Variance (cvxpy)**
* Fractional shares: **ON**

**Expected Output**

* “**Mean-Variance (cvxpy)**” appears in dropdown (only if cvxpy installed)
* Weights differ from Equal-Weight and Inverse-Vol
* All tables and charts render normally

---

## 🧪 Test 5 – Validation: No Strategy Selected

**Steps**

1. Enter any valid amount (e.g., **$5,000**)
2. Select **no strategies**
3. Click **Suggest / Recompute**

**Expected Output**

* Warning: **“Please select at least one strategy.”**
* No allocation table or charts appear

---

## 🧪 Test 6 – Fractional Shares OFF (Whole Shares Only)

**Input**

Use the same inputs as **Test 1**, except:

* Fractional shares: **OFF**

**Expected Output**

* “Shares” column shows **integers only**
* Cash Remaining is **non-zero**
  (whole-share rounding leaves unused cash)
* Other metrics still display correctly

---

## 🧪 Test 7 – Commission & Slippage Effects

**Input**

* Amount: **$5,000**
* Strategy: **Ethical Investing**
* Commission: **$5**
* Slippage: **0.5%**

**Expected Output**

* `ExecPrice` > `Price` for all tickers
  (slippage applied)
* `EstCostUSD` includes **$5 commission** per ticker purchased
* Cash Remaining and Mark-to-Market reflect transaction costs

---

## 🧪 Test 8 – Rebalancing Preview Check

**Steps**

1. Run any allocation where multiple tickers have >0 shares (e.g., Test 2)
2. Scroll to **Rebalancing Preview**

**Expected Output**

* `CurrentW%` and `TargetW%` differ for at least some tickers
* `Diff%` values sum to approximately **0**
  (positive = underweight, negative = overweight)

---

## 🧪 Test 9 – 5-Day Portfolio Trend

**Steps**

1. Run a successful allocation on Day 1
2. Return on a later day (or update `history.json` if allowed)
3. Re-run allocation

**Expected Output**

* Trend chart shows **multiple day values**
* Chart title shows **“Portfolio USD”**
* Up to **5 days** displayed; older entries dropped automatically

---

## 🧪 Test 10 – CSV Export (Allocation & Trade Ticket)

**Steps**

1. Run any successful allocation (e.g., Test 1)
2. Click:

   * **Download Allocation CSV**
   * **Download Trade Ticket CSV**
3. Open both files

**Expected Output**

**Allocation CSV contains:**

* `Ticker`
* `Price`
* `ExecPrice`
* `Weight`
* `Shares`
* `EstCostUSD`

**Trade Ticket CSV contains:**

* `Side`
* `Ticker`
* `Shares`
* `ExecPrice`
* `EstCostUSD`

Both files download and open without errors.
