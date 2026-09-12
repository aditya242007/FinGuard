"""
M4 EDA tests.
"""
import pytest
import pandas as pd
import numpy as np
from src.eda.m4_eda import (
    compute_txn_kpis, compute_cb_kpis, compute_dq_kpis,
    run_validations, compute_outlier_flags
)

@pytest.fixture
def sample_txn():
    """Minimal fake transaction dataframe for unit tests."""
    n = 100
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "txn_id_normalized":   [f"TXN{i:08d}" for i in range(n)],
        "user_id_normalized":  [f"USR{i}" for i in range(n)],
        "merchant_id_normalized": [f"MCH{i%20}" for i in range(n)],
        "amount_numeric":      np.where(rng.random(n) > 0.05, rng.uniform(100, 50000, n), np.nan),
        "status_clean":        rng.choice(["SUCCESS","FAILED","PENDING"], n, p=[0.7,0.2,0.1]),
        "timestamp_clean":     pd.date_range("2024-01-01", periods=n, freq="h"),
        "has_chargeback":      rng.random(n) > 0.9,
        "transaction_has_kyc":      rng.random(n) > 0.3,
        "transaction_has_merchant": rng.random(n) > 0.4,
        "chargeback_count":    np.where(rng.random(n) > 0.9, rng.integers(1, 4, n), np.nan),
        "total_disputed_amount": np.where(rng.random(n) > 0.9, rng.uniform(100, 5000, n), np.nan),
        "chargeback_report_delay_hours": np.where(rng.random(n) > 0.9, rng.uniform(0, 500, n), np.nan),
        "dispute_after_7_days_flag": rng.random(n) > 0.95,
        "utr_missing_flag":          rng.random(n) > 0.8,
        "amount_negative_flag":      rng.random(n) > 0.95,
        "timestamp_invalid_flag":    rng.random(n) > 0.95,
        "duplicate_txn_id_flag":     rng.random(n) > 0.95,
        "referential_integrity_issue_flag": rng.random(n) > 0.5,
        "amount_is_negative":        rng.random(n) > 0.95,
        "amount_is_zero":            rng.random(n) > 0.99,
        "amount_parse_failed":       rng.random(n) > 0.99,
        "amount_missing":            rng.random(n) > 0.99,
        "merchant_category_clean":   rng.choice(["FOOD","RETAIL","TRAVEL"], n),
        "max_severity":              rng.choice(["HIGH","LOW","MEDIUM",""], n),
        "first_chargeback_timestamp": [pd.NaT] * n,
    })
    return df


def test_txn_kpis_count(sample_txn):
    kpis = compute_txn_kpis(sample_txn)
    assert kpis["total_transactions"] == 100

def test_txn_kpis_rates_in_range(sample_txn):
    kpis = compute_txn_kpis(sample_txn)
    assert 0 <= kpis["success_rate_pct"] <= 100
    assert 0 <= kpis["failure_rate_pct"] <= 100
    assert 0 <= kpis["pending_rate_pct"] <= 100

def test_cb_kpis_nonneg(sample_txn):
    cb = pd.DataFrame({
        "txn_id_normalized": [], "chargeback_count": [],
        "total_disputed_amount": [], "max_severity": [],
        "first_chargeback_timestamp": [], "latest_chargeback_timestamp": []
    })
    kpis = compute_cb_kpis(sample_txn, cb)
    assert kpis["chargeback_rate_pct"] >= 0
    assert kpis["disputed_amount_ratio_pct"] >= 0

def test_dq_kpis_pct_in_range(sample_txn):
    kpis = compute_dq_kpis(sample_txn)
    for k, v in kpis.items():
        if k.endswith("_pct"):
            assert 0 <= v <= 100, f"{k}={v} out of range"

def test_outlier_flags_added(sample_txn):
    df = compute_outlier_flags(sample_txn)
    assert "amount_outlier_iqr" in df.columns
    assert "amount_outlier_zscore" in df.columns

def test_validation_all_pass(sample_txn):
    # build a perfectly clean 20k version for the overall count check
    import pandas as pd, numpy as np
    rng = np.random.default_rng(0)
    n = 20_000
    txn = pd.DataFrame({
        "txn_id_normalized":   [f"TXN{i:08d}" for i in range(n)],
        "status_clean":        rng.choice(["SUCCESS","FAILED","PENDING"], n, p=[0.7,0.2,0.1]),
        "timestamp_clean":     pd.date_range("2024-01-01", periods=n, freq="min"),
        "amount_numeric":      rng.uniform(100, 50000, n),
        "has_chargeback":      rng.random(n) > 0.9,
        "transaction_has_kyc":      rng.random(n) > 0.3,
        "transaction_has_merchant": rng.random(n) > 0.4,
        "chargeback_count":    np.where(rng.random(n) > 0.9, rng.integers(1,4,n).astype(float), np.nan),
        "total_disputed_amount": np.where(rng.random(n) > 0.9, rng.uniform(100,5000,n), np.nan),
        "chargeback_report_delay_hours": np.where(rng.random(n)>0.9, rng.uniform(0,500,n), np.nan),
        "dispute_after_7_days_flag": rng.random(n) > 0.95,
        "utr_missing_flag": rng.random(n) > 0.8,
        "amount_negative_flag": rng.random(n) > 0.95,
        "timestamp_invalid_flag": rng.random(n) > 0.95,
        "duplicate_txn_id_flag": rng.random(n) > 0.95,
        "referential_integrity_issue_flag": rng.random(n) > 0.5,
        "amount_is_negative": rng.random(n) > 0.95,
        "amount_is_zero": rng.random(n) > 0.99,
        "amount_parse_failed": rng.random(n) > 0.99,
        "amount_missing": rng.random(n) > 0.99,
        "merchant_category_clean": rng.choice(["FOOD","RETAIL"], n),
        "max_severity": rng.choice(["HIGH","LOW"], n),
        "first_chargeback_timestamp": [pd.NaT]*n,
    })
    kpis = compute_txn_kpis(txn)
    cb = pd.DataFrame({"txn_id_normalized":[], "chargeback_count":[], "total_disputed_amount":[],
                        "max_severity":[], "first_chargeback_timestamp":[], "latest_chargeback_timestamp":[]})
    cb_kpis = compute_cb_kpis(txn, cb)
    results = run_validations(txn, kpis, cb_kpis)
    assert results["txn_count_equals_20000"]
    assert results["success_rate_in_range"]
    assert results["status_rates_sum_le100"]
