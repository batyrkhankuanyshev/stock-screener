"""
Stock Screener
==============
Screens a universe of stocks by fundamental metrics:
  - P/E Ratio
  - EV/EBITDA
  - Revenue Growth (YoY)
  - Return on Equity (ROE)

Usage:
    python screener.py                        # Screen default universe
    python screener.py --tickers AAPL MSFT    # Custom tickers
    python screener.py --output results.csv   # Save to CSV
    python screener.py --top 10               # Show top N stocks
"""

import argparse
import sys
import time
from datetime import datetime

import pandas as pd
import yfinance as yf
from tabulate import tabulate

# ── Default stock universe ────────────────────────────────────────────────────
DEFAULT_TICKERS = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "ORCL", "CRM", "ADBE", "INTC",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "AXP", "V", "MA",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT",
    # Consumer
    "AMZN", "TSLA", "WMT", "HD", "NKE", "SBUX", "MCD", "KO", "PEP",
    # Industrials
    "CAT", "BA", "HON", "GE", "MMM", "UPS", "FDX",
]

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHTS = {
    "pe_score":          0.25,   # Lower P/E = cheaper valuation
    "ev_ebitda_score":   0.25,   # Lower EV/EBITDA = cheaper
    "revenue_growth_score": 0.30, # Higher growth = better
    "roe_score":         0.20,   # Higher ROE = better capital efficiency
}


def fetch_fundamentals(ticker: str) -> dict:
    """Fetch key fundamental metrics for a single ticker via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Pull financials for revenue growth
        financials = stock.financials  # annual income statement

        revenue_growth = None
        if financials is not None and not financials.empty:
            if "Total Revenue" in financials.index and financials.shape[1] >= 2:
                rev_recent = financials.loc["Total Revenue"].iloc[0]
                rev_prior  = financials.loc["Total Revenue"].iloc[1]
                if rev_prior and rev_prior != 0:
                    revenue_growth = (rev_recent - rev_prior) / abs(rev_prior) * 100

        return {
            "ticker":         ticker,
            "name":           info.get("shortName", ticker),
            "sector":         info.get("sector", "N/A"),
            "pe_ratio":       info.get("trailingPE"),
            "ev_ebitda":      info.get("enterpriseToEbitda"),
            "revenue_growth": revenue_growth,
            "roe":            (info.get("returnOnEquity") or 0) * 100,  # convert to %
            "market_cap":     info.get("marketCap"),
            "price":          info.get("currentPrice") or info.get("regularMarketPrice"),
        }

    except Exception as e:
        print(f"  [WARN] {ticker}: {e}")
        return None


def fetch_all(tickers: list, delay: float = 0.3) -> pd.DataFrame:
    """Fetch fundamentals for all tickers with a small delay to be polite."""
    records = []
    total = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        print(f"  Fetching {ticker:<6}  ({i}/{total})", end="\r")
        result = fetch_fundamentals(ticker)
        if result:
            records.append(result)
        time.sleep(delay)

    print(" " * 50, end="\r")  # clear progress line
    return pd.DataFrame(records)


# ── Scoring helpers ───────────────────────────────────────────────────────────

def percentile_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    """
    Rank each value as a percentile 0–100.
    ascending=True  → lower raw value gets a HIGHER score (cheaper is better)
    ascending=False → higher raw value gets a HIGHER score (growth is better)
    """
    if ascending:
        return series.rank(ascending=True, pct=True) * 100
    else:
        return series.rank(ascending=False, pct=True) * 100


def score(df: pd.DataFrame) -> pd.DataFrame:
    """Add individual metric scores and a composite score to the DataFrame."""
    df = df.copy()

    # Only score rows where the metric is available
    for col, score_col, asc in [
        ("pe_ratio",       "pe_score",             True),
        ("ev_ebitda",      "ev_ebitda_score",       True),
        ("revenue_growth", "revenue_growth_score",  False),
        ("roe",            "roe_score",             False),
    ]:
        valid = df[col].notna()
        df[score_col] = None
        df.loc[valid, score_col] = percentile_rank(df.loc[valid, col], ascending=asc)

    # Composite weighted score (only for rows with all four metrics)
    score_cols = list(WEIGHTS.keys())
    has_all = df[score_cols].notna().all(axis=1)
    df["composite_score"] = None
    df.loc[has_all, "composite_score"] = sum(
        df.loc[has_all, col] * w for col, w in WEIGHTS.items()
    )

    return df


def rank_and_display(df: pd.DataFrame, top_n: int = None) -> pd.DataFrame:
    """Sort by composite score, optionally limit rows, and return display df."""
    df = df.dropna(subset=["composite_score"]).copy()
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    df.index += 1  # 1-based rank

    if top_n:
        df = df.head(top_n)

    display = df[[
        "ticker", "name", "sector",
        "pe_ratio", "ev_ebitda", "revenue_growth", "roe",
        "pe_score", "ev_ebitda_score", "revenue_growth_score", "roe_score",
        "composite_score",
        "market_cap", "price",
    ]].copy()

    # Format columns
    display["pe_ratio"]       = display["pe_ratio"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    display["ev_ebitda"]      = display["ev_ebitda"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    display["revenue_growth"] = display["revenue_growth"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    display["roe"]            = display["roe"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    display["market_cap"]     = display["market_cap"].map(
        lambda x: f"${x/1e9:.1f}B" if pd.notna(x) and x else "N/A"
    )
    display["price"]          = display["price"].map(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")

    for sc in ["pe_score", "ev_ebitda_score", "revenue_growth_score", "roe_score", "composite_score"]:
        display[sc] = display[sc].map(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")

    display.columns = [
        "Ticker", "Name", "Sector",
        "P/E", "EV/EBITDA", "Rev Growth", "ROE",
        "P/E Score", "EV Score", "Growth Score", "ROE Score",
        "⭐ Score",
        "Mkt Cap", "Price",
    ]
    return display


def print_results(display_df: pd.DataFrame) -> None:
    """Pretty-print results to the terminal."""
    print("\n" + "═" * 80)
    print(f"  📊  STOCK SCREENER RESULTS  —  {datetime.now().strftime('%Y-%m-%d')}")
    print("═" * 80)
    print(tabulate(
        display_df,
        headers="keys",
        tablefmt="rounded_outline",
        showindex=True,
    ))
    print("\n  Scoring: P/E (25%) · EV/EBITDA (25%) · Revenue Growth (30%) · ROE (20%)")
    print("  Scores are percentile ranks within the screened universe (higher = better).\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Fundamental stock screener")
    parser.add_argument(
        "--tickers", nargs="+", metavar="TICKER",
        help="Space-separated list of tickers (default: built-in universe)",
    )
    parser.add_argument(
        "--top", type=int, default=None, metavar="N",
        help="Show only the top N stocks",
    )
    parser.add_argument(
        "--output", metavar="FILE",
        help="Save results to CSV (e.g. results.csv)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.3, metavar="SECS",
        help="Delay between API requests in seconds (default 0.3)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_TICKERS

    print(f"\n🔍  Screening {len(tickers)} stocks …")
    raw_df = fetch_all(tickers, delay=args.delay)

    if raw_df.empty:
        print("No data retrieved. Check your internet connection or ticker list.")
        sys.exit(1)

    scored_df  = score(raw_df)
    display_df = rank_and_display(scored_df, top_n=args.top)
    print_results(display_df)

    if args.output:
        display_df.to_csv(args.output)
        print(f"  ✅  Results saved to {args.output}\n")

    return display_df


if __name__ == "__main__":
    main()
