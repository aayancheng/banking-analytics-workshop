"""The deny-list is enforced, not aspirational."""
import pandas as pd

from shared.config import LEAKAGE_COLUMNS, RAW
from score.src.feature_engineering import FEATURE_COLUMNS
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS


def test_score_features_are_leakage_free():
    assert set(FEATURE_COLUMNS).isdisjoint(LEAKAGE_COLUMNS)


def test_adjudication_features_are_leakage_free():
    assert set(ADJ_FEATURE_COLUMNS).isdisjoint(LEAKAGE_COLUMNS)


def test_denied_columns_actually_exist_in_data():
    """A deny-list of typos protects nothing."""
    biz = pd.read_parquet(RAW / "businesses.parquet")
    portfolio = pd.read_parquet(RAW / "portfolio.parquet")
    present = set(biz.columns) | set(portfolio.columns)
    assert set(LEAKAGE_COLUMNS) <= present
