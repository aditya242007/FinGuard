"""
Integration tests for Milestone 3.
"""
import pandas as pd
import numpy as np
from src.integration.build_model import resolve_entities, aggregate_chargebacks

def test_resolve_entities():
    # Mock data with duplicates
    data = {
        "user_id_normalized": ["U1", "U1", "U2", "U2", "U3"],
        "signup_timestamp_clean": ["2023-01-01", "2023-01-02", "2023-01-01", pd.NaT, "2023-01-01"],
        "col1": ["A", "A", "B", None, "C"]
    }
    df = pd.DataFrame(data)
    
    canonical, dup_count = resolve_entities(df, "user_id_normalized", ["signup_timestamp_clean"], [False])
    
    assert len(canonical) == 3
    assert dup_count == 2
    
    # U1 should pick the latest date (2023-01-02) because completeness is same
    assert canonical.loc[canonical["user_id_normalized"] == "U1", "signup_timestamp_clean"].iloc[0] == "2023-01-02"
    
    # U2 should pick the first because it's more complete (col1 is not null)
    assert canonical.loc[canonical["user_id_normalized"] == "U2", "signup_timestamp_clean"].iloc[0] == "2023-01-01"

def test_aggregate_chargebacks():
    data = {
        "txn_id_normalized": ["T1", "T1", "T2"],
        "complaint_id_normalized": ["C1", "C2", "C3"],
        "disputed_amount_numeric": [100.0, 50.0, 200.0],
        "severity_clean": ["HIGH", "LOW", "MEDIUM"],
        "transaction_timestamp_clean": ["2023-01-01", "2023-01-01", "2023-01-01"],
        "reported_timestamp_clean": ["2023-01-02", "2023-01-03", "2023-01-02"],
        "bank_response_timestamp_clean": ["2023-01-03", "2023-01-04", "2023-01-03"]
    }
    df = pd.DataFrame(data)
    
    agg = aggregate_chargebacks(df)
    
    assert len(agg) == 2
    t1_agg = agg[agg["txn_id_normalized"] == "T1"].iloc[0]
    
    assert t1_agg["chargeback_count"] == 2
    assert t1_agg["total_disputed_amount"] == 150.0
    assert "HIGH" in t1_agg["max_severity"] and "LOW" in t1_agg["max_severity"]
    
    # Dates converted internally
    assert pd.to_datetime(t1_agg["first_chargeback_timestamp"]) == pd.to_datetime("2023-01-02")
    assert pd.to_datetime(t1_agg["latest_chargeback_timestamp"]) == pd.to_datetime("2023-01-03")
