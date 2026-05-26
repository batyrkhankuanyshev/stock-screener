"""
Unit tests for the stock screener.
Run with:  pytest tests/test_screener.py -v
"""

import pandas as pd
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from screener import score, rank_and_display, percentile_rank, WEIGHTS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Small synthetic DataFrame that mimics fetched data."""
    return pd.DataFrame([
        {"ticker": "CHEAP", "name": "Cheap Co",  "sector": "Tech",    "pe_ratio": 8.0,  "ev_ebitda": 5.0,  "revenue_growth": 20.0, "roe": 25.0, "market_cap": 50e9,  "price": 100.0},
        {"ticker": "MID",   "name": "Mid Co",    "sector": "Finance",  "pe_ratio": 18.0, "ev_ebitda": 12.0, "revenue_growth": 10.0, "roe": 12.0, "market_cap": 200e9, "price": 250.0},
        {"ticker": "PRICEY","name": "Pricey Co", "sector": "Consumer", "pe_ratio": 40.0, "ev_ebitda": 30.0, "revenue_growth": 2.0,  "roe": 5.0,  "market_cap": 800e9, "price": 500.0},
    ])


@pytest.fixture
def missing_df():
    """DataFrame with some missing metrics."""
    return pd.DataFrame([
        {"ticker": "A", "name": "A Co", "sector": "X", "pe_ratio": None, "ev_ebitda": 5.0, "revenue_growth": 15.0, "roe": 20.0, "market_cap": 1e9, "price": 50.0},
        {"ticker": "B", "name": "B Co", "sector": "X", "pe_ratio": 10.0, "ev_ebitda": 8.0, "revenue_growth": 10.0, "roe": 10.0, "market_cap": 2e9, "price": 80.0},
    ])


# ── percentile_rank ───────────────────────────────────────────────────────────

class TestPercentileRank:
    def test_ascending_lower_is_better(self):
        s = pd.Series([10, 20, 30])
        ranks = percentile_rank(s, ascending=True)
        # lowest value should have highest rank score
        assert ranks.iloc[0] > ranks.iloc[2]

    def test_descending_higher_is_better(self):
        s = pd.Series([10, 20, 30])
        ranks = percentile_rank(s, ascending=False)
        assert ranks.iloc[2] > ranks.iloc[0]

    def test_all_same_values(self):
        s = pd.Series([5, 5, 5])
        ranks = percentile_rank(s)
        # should not raise; all equal rank
        assert ranks.notna().all()

    def test_single_value(self):
        s = pd.Series([42])
        ranks = percentile_rank(s)
        assert len(ranks) == 1


# ── score ─────────────────────────────────────────────────────────────────────

class TestScore:
    def test_score_columns_created(self, sample_df):
        result = score(sample_df)
        for col in WEIGHTS:
            assert col in result.columns
        assert "composite_score" in result.columns

    def test_cheap_has_higher_composite(self, sample_df):
        result = score(sample_df)
        cheap_score  = result.loc[result["ticker"] == "CHEAP",  "composite_score"].iloc[0]
        pricey_score = result.loc[result["ticker"] == "PRICEY", "composite_score"].iloc[0]
        assert cheap_score > pricey_score

    def test_scores_between_0_and_100(self, sample_df):
        result = score(sample_df)
        for col in WEIGHTS:
            valid = result[col].dropna()
            assert (valid >= 0).all() and (valid <= 100).all()

    def test_missing_metric_excluded_from_composite(self, missing_df):
        result = score(missing_df)
        # Ticker A is missing pe_ratio → composite should be NaN
        a_composite = result.loc[result["ticker"] == "A", "composite_score"].iloc[0]
        b_composite = result.loc[result["ticker"] == "B", "composite_score"].iloc[0]
        assert pd.isna(a_composite)
        assert pd.notna(b_composite)

    def test_original_df_not_mutated(self, sample_df):
        original_cols = set(sample_df.columns)
        _ = score(sample_df)
        assert set(sample_df.columns) == original_cols


# ── rank_and_display ──────────────────────────────────────────────────────────

class TestRankAndDisplay:
    def test_sorted_descending(self, sample_df):
        scored = score(sample_df)
        display = rank_and_display(scored)
        scores = [float(s) for s in display["⭐ Score"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limits_rows(self, sample_df):
        scored = score(sample_df)
        display = rank_and_display(scored, top_n=2)
        assert len(display) == 2

    def test_index_starts_at_1(self, sample_df):
        scored = score(sample_df)
        display = rank_and_display(scored)
        assert display.index[0] == 1

    def test_returns_dataframe(self, sample_df):
        scored = score(sample_df)
        display = rank_and_display(scored)
        assert isinstance(display, pd.DataFrame)

    def test_missing_composite_excluded(self, missing_df):
        scored = score(missing_df)
        display = rank_and_display(scored)
        # Only ticker B has a composite score
        assert len(display) == 1
        assert "B" in display["Ticker"].values


# ── weights sum to 1 ──────────────────────────────────────────────────────────

class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"
