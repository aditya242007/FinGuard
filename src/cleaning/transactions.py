"""
Transaction Cleaning.
"""
from __future__ import annotations
import pandas as pd
from src.cleaning.ids import normalize_txn_id, normalize_user_id, normalize_merchant_id
from src.cleaning.amounts import clean_amount_series
from src.cleaning.timestamps import clean_timestamp_series
from src.cleaning.statuses import normalize_txn_status
from src.cleaning.utr import clean_utr_series
from src.cleaning.mcc import clean_mcc_series

def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean transaction dataset."""
    df_clean = df.copy()
    stats = {"raw_rows": len(df)}
    
    # Track exact duplicates before we do anything
    dup_mask = df_clean.duplicated(keep="first")
    stats["exact_duplicates_removed"] = int(dup_mask.sum())
    df_clean = df_clean[~dup_mask].copy()
    
    # ID Normalization
    df_clean["original_txn_id"] = df_clean["txn_id"]
    df_clean["txn_id_normalized"] = df_clean["txn_id"].apply(normalize_txn_id)
    
    df_clean["original_user_id"] = df_clean["user_id"]
    df_clean["user_id_normalized"] = df_clean["user_id"].apply(normalize_user_id)
    
    df_clean["original_merchant_id"] = df_clean["merchant_id"]
    df_clean["merchant_id_normalized"] = df_clean["merchant_id"].apply(normalize_merchant_id)
    
    # Duplicates flags
    df_clean["txn_id_duplicate_count"] = df_clean.groupby("txn_id_normalized")["txn_id_normalized"].transform("count")
    df_clean["txn_id_is_duplicate"] = df_clean["txn_id_duplicate_count"] > 1
    
    # Amounts
    if "amount" in df_clean.columns:
        amt_df = clean_amount_series(df_clean["amount"], "amount")
        df_clean = pd.concat([df_clean, amt_df], axis=1)
        
    # Timestamps
    if "timestamp" in df_clean.columns:
        ts_df = clean_timestamp_series(df_clean["timestamp"], "timestamp")
        df_clean = pd.concat([df_clean, ts_df], axis=1)
        
    # UTR
    if "utr" in df_clean.columns:
        utr_df = clean_utr_series(df_clean["utr"])
        df_clean = pd.concat([df_clean, utr_df], axis=1)
        
    # MCC
    if "mcc" in df_clean.columns:
        mcc_df = clean_mcc_series(df_clean["mcc"])
        df_clean = pd.concat([df_clean, mcc_df], axis=1)
        
    # Status
    if "status" in df_clean.columns:
        df_clean["status_raw"] = df_clean["status"]
        df_clean["status_clean"] = df_clean["status"].apply(normalize_txn_status)
        
    # Lineage
    df_clean["source_dataset"] = "track1_upi_transactions"
    # Keeping the index as proxy for source row number since we dropped exact duplicates
    df_clean["source_row_number"] = df_clean.index.astype(str)
    
    stats["processed_rows"] = len(df_clean)
    
    return df_clean, stats
