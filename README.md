# Mutual Fund Quantitative Researcher & 5-Year Rolling Screener

A Python-based quantitative mutual fund research tool that analyzes mutual funds with at least **9 years of track record**, computes **5-year rolling CAGR returns** across historical market cycles (bull, bear, and sideways regimes), evaluates expense ratios (TER) and AUM scale, and calculates a composite **rating out of 10**.

---

## 🌟 Key Highlights

1. **Category-Wide Quantitative Research**:
   - Searches funds dynamically using Dhan's `SearchScript` API for any subcategory (default: `Flexi Cap Fund`, plus `Large Cap Fund`, `Mid Cap Fund`, `Small Cap Fund`, `ELSS`, `Multi Cap Fund`, etc.).
   - Filters only funds that have been active for **>= 9 years since inception**.

2. **5-Year Rolling Return Engine (Benchmark Across Cycles)**:
   - Fetches historical daily NAV data using Dhan's `chart` API with `sCode` (`dmfm_cmots_scheme_code`).
   - Computes rolling 5-year CAGR over 1,200+ trading windows:
     $$\text{CAGR}_{5Y} = \left(\frac{\text{NAV}_t}{\text{NAV}_{t-5Y}}\right)^{1/5} - 1$$
   - Captures comprehensive cycle statistics:
     - **Average 5Y Rolling Return (CAGR %)**
     - **Median 5Y Rolling Return (%)**
     - **Downside Resilience (Worst 5Y period Min CAGR %)**
     - **Best 5Y period Max CAGR (%)**
     - **Rolling Return Volatility (Standard Deviation %)**
     - **Probability of beating 10%, 12%, and 15% hurdle rates**
     - **Probability of negative return periods (< 0%)**

3. **Multi-Factor Quantitative Rating (Out of 10.0)**:
   - **5-Year Rolling Return Performance (3.5 Points)**: Evaluates rolling mean CAGR (2.0 pts) and downside resilience in the worst 5Y period (1.5 pts).
   - **Expense Ratio / TER (2.5 Points - High Weightage)**: Rewards low-cost funds that minimize fee drag over multi-decade compounding.
   - **Consistency & Volatility (2.0 Points)**: Rewards high probability (>12% CAGR) and lower rolling return standard deviation.
   - **AUM Scale Factor (1.0 Point - Lesser Weightage)**: Ensures fund liquidity and stability without unfairly penalizing agile mid-sized funds.
   - **Trailing 5Y Return (1.0 Point)**: Validates point-to-point trailing returns from the Dhan API.
   - **Minimum SIP Amount**: Displayed prominently in the table and modal, excluded from rating calculation as requested.

4. **Interactive Dashboard & Locked Modal System**:
   - **Research workspace**: Warm-charcoal dark surfaces, restrained amber actions, and category controls beside the results on wide screens. Phones show each fund as a labeled record without dropping metrics.
   - **Accessible interactions**: Visible keyboard focus, arrow-key analysis tabs, focus containment and restoration in the locked modal, reduced-motion support, and inline loading/error/retry states.
   - **Design tokens**: `tokens.css` is served at `/tokens.css`; `static/css/research.css` applies the current design over the preserved base stylesheet.
   - **Table**: Shows Rank, Rating Badge, Scheme Name, Inception (Age), AUM, TER, 5Y Rolling Avg/Min/Max, 5Y Trailing Return, and Min SIP.
   - **Locked Modal Window**: **Backdrop clicks and Escape do NOT dismiss the modal**. An outline and message direct the user to the dedicated `[✕]` or `Close` button.
   - **Tabular Comparison**: Shows precalculated API returns side-by-side with 5-year rolling return statistics.
   - **Rolling Return Timeline Chart**: Interactive chart visualizer showing the fund's 5-year rolling CAGR through every market phase.

5. **SQLite Caching**:
   - Automatically caches downloaded schemes, computed rolling metrics, and chart series into `mutual_fund_cache.db`.
   - Subsequent searches load in **< 5 milliseconds**.
   - Includes a **Force Live Refresh** toggle to re-fetch live data on demand.

6. **Investment Growth Calculator**:
   - Select a fund using **View analysis**, then open its **Calculator** tab to compare monthly SIP and lump-sum scenarios for that specific scheme.
   - Enter the monthly or one-time investment amount in INR, expected annual return (%), and a positive whole-number duration in years.
   - Calculates estimated future value, total invested amount, and estimated gains (or losses), formatted in INR.
   - Starts with the selected fund's reported minimum monthly SIP and average 5-year rolling CAGR. Both are editable; monthly SIP amounts must meet the reported minimum, while lump-sum amounts do not inherit that SIP limit.
   - The rolling CAGR is explicitly labeled as a historical reference, not a forecast or historical SIP return. Missing minimum SIP or usable rolling-return data leaves the relevant field blank with an explanation.
   - Runs entirely in the browser after a fund is selected. Opening another fund resets the form and results so projections cannot carry over under the wrong scheme. Editing assumptions clears the previous estimate until **Calculate growth** is selected again.
   - SIP assumes equal **month-end** payments and a monthly rate `r = annual return / 100 / 12`: `FV = amount × ((1 + r)^(12 × years) - 1) / r`. At zero return, `FV = amount × 12 × years`.
   - Lump sum compounds annually: `FV = amount × (1 + annual return / 100)^years`.
   - Returns may be zero or negative, but must be greater than -100%. Estimates assume a constant return and exclude taxes, fees, inflation, withdrawals, and SIP increases; they are not guaranteed outcomes.

---

## 🚀 Getting Started

### 1. Prerequisites & Virtual Environment using `uv`

Using [`uv`](https://github.com/astral-sh/uv) (recommended):

```bash
# Automatically creates .venv and installs all dependencies
uv sync

# Or activate the virtual environment manually:
source .venv/bin/activate
```

### 2. Launch the Application

```bash
# Using uv directly:
uv run python run.py

# Or using the activated virtual environment:
python run.py
```

Open your browser at:
```
http://127.0.0.1:8000
```

---

## 📊 Scoring Model Summary

| Factor | Weight | Max Points | Key Criteria |
| :--- | :---: | :---: | :--- |
| **5Y Rolling Return Performance** | 35% | **3.5** | Rolling mean CAGR (2.0 pts) + Downside Min 5Y CAGR (1.5 pts) |
| **Expense Ratio (TER)** | 25% | **2.5** | Higher points for lower TER ($\le 0.70\%$ gets full points) |
| **Consistency & Volatility** | 20% | **2.0** | Probability of CAGR $> 12\%$ (1.0 pt) + Low Std Dev (1.0 pt) |
| **AUM Scale Factor** | 10% | **1.0** | Liquidity and scale stability (higher score for stable AUM) |
| **Trailing 5Y Return** | 10% | **1.0** | API precalculated trailing 5-year return validation |
| **Minimum SIP Amount** | 0% | **0.0** | Displayed for informational convenience (no rating impact) |
| **Total Composite Rating** | **100%** | **10.0** | Classified into Elite, Excellent, Good, Moderate, Weak |

---

## 🛠 Project Structure

```
mutual-fund-researcher/
├── app/
│   ├── dhan_client.py     # Dhan SearchScript & Chart API integrations
│   ├── rolling_calc.py    # 5-Year rolling return engine & statistics
│   ├── rating_engine.py   # Multi-factor scoring model out of 10
│   ├── cache_db.py        # SQLite caching layer for instant responses
│   ├── models.py          # Pydantic schemas and dataclasses
│   ├── researcher.py      # Core research service
│   └── main.py            # FastAPI endpoints and static routing
├── static/
│   ├── css/style.css      # Preserved base component styles
│   ├── css/research.css   # Responsive Midnight research workspace
│   ├── js/app.js          # Interactive table, locked modal & Chart.js
│   ├── js/investment-growth.mjs     # Validated SIP and lump-sum calculations
│   ├── js/investment-calculator.mjs # Calculator form and result display
│   └── index.html         # Main dashboard interface
├── requirements.txt       # Python dependencies
├── tokens.css             # Shared color, type, spacing and motion tokens
├── run.py                 # Startup script
└── mutual_fund_cache.db   # SQLite cache database
```

Calculator regression tests use Node.js's built-in runner (Node.js 18+; no npm dependencies):

```powershell
node --test .\tests\investment-growth.test.mjs
```
