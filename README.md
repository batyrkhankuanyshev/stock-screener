# 📊 Stock Screener

A command-line fundamental stock screener that pulls live financial data and ranks equities by valuation and quality metrics — the kind of first-pass analysis an investment analyst runs every morning.

## Features

- **Live data** via [yfinance](https://github.com/ranaroussi/yfinance) (no API key required)
- **Four core metrics**: P/E Ratio, EV/EBITDA, Revenue Growth (YoY), Return on Equity
- **Composite scoring**: percentile-rank each metric within the universe, then blend with configurable weights
- **Flexible CLI**: screen the built-in 40-stock universe, or pass your own tickers
- **CSV export** for further analysis in Excel / pandas
- **Unit-tested** scoring logic (pytest)

## Methodology

Each stock receives a score from 0–100 on each metric (percentile rank within the screened universe):

| Metric | Direction | Weight |
|---|---|---|
| P/E Ratio | Lower = better (cheaper) | 25% |
| EV/EBITDA | Lower = better (cheaper) | 25% |
| Revenue Growth YoY | Higher = better | 30% |
| Return on Equity | Higher = better | 20% |

The **Composite Score** is a weighted average of the four metric scores. Stocks missing any metric are excluded from ranking (but still appear in the raw data).

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/stock-screener.git
cd stock-screener

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the screener
python screener.py
```

## Usage

```bash
# Screen default 40-stock universe
python screener.py

# Screen only specific tickers
python screener.py --tickers AAPL MSFT GOOGL NVDA TSM

# Show only the top 10 stocks
python screener.py --top 10

# Save results to CSV
python screener.py --output results.csv

# Combine flags
python screener.py --top 15 --output top15.csv
```

## Sample Output

```
════════════════════════════════════════════════════════════════════════════════
  📊  STOCK SCREENER RESULTS  —  2024-11-20
════════════════════════════════════════════════════════════════════════════════
╭──────┬────────┬──────────────────┬───────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┬──────────────┬───────────╮
│  #   │ Ticker │ Name             │ Sector    │  P/E     │ EV/EBITDA│ Rev Growth│  ROE     │ P/E Score│ Growth Score │  ⭐ Score    │  Mkt Cap  │
├──────┼────────┼──────────────────┼───────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────────┼──────────────┼───────────┤
│   1  │ NVDA   │ NVIDIA Corp      │ Tech      │  35.2    │  22.1    │  122.4%  │  123.7%  │  61.5    │  100.0       │  88.3        │ $3,300.0B │
│   2  │ META   │ Meta Platforms   │ Comm Svcs │  23.8    │  14.5    │   19.8%  │   34.2%  │  76.9    │   73.1       │  76.1        │ $1,500.0B │
│   3  │ MSFT   │ Microsoft Corp   │ Tech      │  31.4    │  21.0    │   15.7%  │   37.8%  │  65.4    │   65.4       │  70.8        │ $3,100.0B │
╰──────┴────────┴──────────────────┴───────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┴──────────────┴───────────╯

  Scoring: P/E (25%) · EV/EBITDA (25%) · Revenue Growth (30%) · ROE (20%)
  Scores are percentile ranks within the screened universe (higher = better).
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Project Structure

```
stock-screener/
├── screener.py          # Main script
├── requirements.txt     # Dependencies
├── tests/
│   └── test_screener.py # Unit tests
└── README.md
```

## Customising the Weights

Open `screener.py` and edit the `WEIGHTS` dictionary at the top:

```python
WEIGHTS = {
    "pe_score":             0.25,
    "ev_ebitda_score":      0.25,
    "revenue_growth_score": 0.30,
    "roe_score":            0.20,
}
```

Values must sum to 1.0.

## Limitations & Caveats

- Data is sourced from Yahoo Finance via `yfinance`; accuracy depends on Yahoo's data pipeline
- Financials use trailing (TTM) figures where available
- Stocks with missing metrics (e.g. negative EBITDA, no reported earnings) are excluded from the ranked table
- This is a screening tool, not a buy/sell recommendation

## License

MIT
