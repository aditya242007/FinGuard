import pandas as pd
import pytest
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROCESSED_DIR = HERE / "data" / "processed"
FEATURES_DIR = PROCESSED_DIR / "features"

@pytest.fixture(scope="module")
def datasets():
    txn_m3 = pd.read_csv(PROCESSED_DIR / "finguard_transactions.csv", dtype=str)
    usr_m3 = pd.read_csv(PROCESSED_DIR / "users_analytics.csv", dtype=str)
    mrc_m3 = pd.read_csv(PROCESSED_DIR / "merchants_analytics.csv", dtype=str)
    cb_m3 = pd.read_csv(PROCESSED_DIR / "chargebacks_aggregated.csv", dtype=str)
    
    txn_f = pd.read_csv(FEATURES_DIR / "transaction_risk_features.csv")
    usr_f = pd.read_csv(FEATURES_DIR / "user_risk_features.csv")
    mrc_f = pd.read_csv(FEATURES_DIR / "merchant_risk_features.csv")
    cb_f = pd.read_csv(FEATURES_DIR / "chargeback_risk_features.csv")
    
    return {
        "txn_m3": txn_m3, "usr_m3": usr_m3, "mrc_m3": mrc_m3, "cb_m3": cb_m3,
        "txn_f": txn_f, "usr_f": usr_f, "mrc_f": mrc_f, "cb_f": cb_f
    }

def test_row_counts(datasets):
    assert len(datasets["txn_f"]) == len(datasets["txn_m3"])
    assert len(datasets["usr_f"]) == len(datasets["txn_m3"]["user_id_normalized"].dropna().unique())
    assert len(datasets["mrc_f"]) == len(datasets["txn_m3"]["merchant_id_normalized"].dropna().unique())
    assert len(datasets["cb_f"]) == len(datasets["cb_m3"])

def test_uniqueness(datasets):
    assert datasets["txn_f"]["txn_id_normalized"].is_unique
    assert datasets["usr_f"]["user_id_normalized"].is_unique
    assert datasets["mrc_f"]["merchant_id_normalized"].is_unique

def test_no_join_explosion(datasets):
    assert len(datasets["txn_f"]) == len(datasets["txn_m3"])

def test_negative_amounts_preserved(datasets):
    neg_count = datasets["txn_f"]["negative_amount_flag"].sum()
    assert neg_count > 0, "Negative amounts should be preserved, none found."
    assert (datasets["txn_f"]["amount_numeric"] < 0).sum() == neg_count

def test_no_infinite_values(datasets):
    # Transaction features
    num_cols = datasets["txn_f"].select_dtypes(include=[np.number]).columns
    assert not np.isinf(datasets["txn_f"][num_cols]).any().any()
    
    # User features
    num_cols = datasets["usr_f"].select_dtypes(include=[np.number]).columns
    assert not np.isinf(datasets["usr_f"][num_cols]).any().any()

def test_min_sample_size_behavior(datasets):
    # If a user has < 5 transactions, user_amount_zscore should be NaN
    user_counts = datasets["txn_f"]["user_id_normalized"].value_counts()
    small_users = user_counts[user_counts < 5].index
    small_txn = datasets["txn_f"][datasets["txn_f"]["user_id_normalized"].isin(small_users)]
    if not small_txn.empty:
        assert small_txn["user_amount_zscore"].isna().all()

def test_chargeback_aggregation(datasets):
    # Total disputed amount across users should roughly match if it was uniquely assigned,
    # but chargebacks can have a 1:M user if multiple chargebacks. 
    # Just check no NaN in critical rates
    assert datasets["usr_f"]["chargeback_rate"].notna().all()
    assert (datasets["usr_f"]["chargeback_rate"] <= 1.0).all()
    assert (datasets["mrc_f"]["chargeback_rate"] <= 1.0).all()

