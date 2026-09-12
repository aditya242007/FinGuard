"""
Chargeback Cleaning.
"""
from __future__ import annotations
import pandas as pd
from src.cleaning.ids import normalize_txn_id, normalize_user_id, normalize_merchant_id, normalize_complaint_id
from src.cleaning.amounts import clean_amount_series
from src.cleaning.timestamps import clean_timestamp_series
from src.cleaning.statuses import canonicalize_generic

def clean_chargebacks(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean Chargebacks dataset."""
    df_clean = df.copy()
    stats = {"raw_rows": len(df)}
    
    dup_mask = df_clean.duplicated(keep="first")
    stats["exact_duplicates_removed"] = int(dup_mask.sum())
    df_clean = df_clean[~dup_mask].copy()
    
    # ID Normalization
    df_clean["original_complaint_id"] = df_clean["complaint_id"]
    df_clean["complaint_id_normalized"] = df_clean["complaint_id"].apply(normalize_complaint_id)
    
    df_clean["complaint_id_duplicate_count"] = df_clean.groupby("complaint_id_normalized")["complaint_id_normalized"].transform("count")
    df_clean["complaint_id_is_duplicate"] = df_clean["complaint_id_duplicate_count"] > 1
    
    if "txn_id" in df_clean.columns:
        df_clean["original_txn_id"] = df_clean["txn_id"]
        df_clean["txn_id_normalized"] = df_clean["txn_id"].apply(normalize_txn_id)
        
    if "user_id" in df_clean.columns:
        df_clean["original_user_id"] = df_clean["user_id"]
        df_clean["user_id_normalized"] = df_clean["user_id"].apply(normalize_user_id)
        
    if "merchant_id" in df_clean.columns:
        df_clean["original_merchant_id"] = df_clean["merchant_id"]
        df_clean["merchant_id_normalized"] = df_clean["merchant_id"].apply(normalize_merchant_id)
        
    # Amounts
    if "disputed_amount" in df_clean.columns:
        amt_df = clean_amount_series(df_clean["disputed_amount"], "disputed_amount")
        df_clean = pd.concat([df_clean, amt_df], axis=1)
        
    # Timestamps
    for ts_col in ["transaction_timestamp", "reported_timestamp", "bank_response_timestamp"]:
        if ts_col in df_clean.columns:
            ts_df = clean_timestamp_series(df_clean[ts_col], ts_col)
            df_clean = pd.concat([df_clean, ts_df], axis=1)
            
    # Categoricals
    for col in ["reason_code", "resolution_status", "severity", "channel"]:
        if col in df_clean.columns:
            df_clean[f"{col}_raw"] = df_clean[col]
            df_clean[f"{col}_clean"] = df_clean[col].apply(canonicalize_generic)
            
    df_clean["source_dataset"] = "track1_chargebacks"
    df_clean["source_row_number"] = df_clean.index.astype(str)
    
    stats["processed_rows"] = len(df_clean)
    
    return df_clean, stats
