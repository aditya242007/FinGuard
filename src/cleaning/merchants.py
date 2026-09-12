"""
Merchant Cleaning.
"""
from __future__ import annotations
import pandas as pd
from src.cleaning.ids import normalize_merchant_id
from src.cleaning.amounts import clean_amount_series
from src.cleaning.timestamps import clean_timestamp_series
from src.cleaning.statuses import normalize_merchant_status, canonicalize_generic
from src.cleaning.mcc import clean_mcc_series

def clean_merchants(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean Merchant dataset."""
    df_clean = df.copy()
    stats = {"raw_rows": len(df)}
    
    dup_mask = df_clean.duplicated(keep="first")
    stats["exact_duplicates_removed"] = int(dup_mask.sum())
    df_clean = df_clean[~dup_mask].copy()
    
    # ID Normalization
    df_clean["original_merchant_id"] = df_clean["merchant_id"]
    df_clean["merchant_id_normalized"] = df_clean["merchant_id"].apply(normalize_merchant_id)
    
    df_clean["merchant_duplicate_group"] = df_clean.groupby("merchant_id_normalized").ngroup()
    
    # MCC
    if "mcc" in df_clean.columns:
        mcc_df = clean_mcc_series(df_clean["mcc"])
        df_clean = pd.concat([df_clean, mcc_df], axis=1)
        
    # Amounts
    if "declared_avg_ticket_size" in df_clean.columns:
        amt_df = clean_amount_series(df_clean["declared_avg_ticket_size"], "declared_avg_ticket_size")
        df_clean = pd.concat([df_clean, amt_df], axis=1)
        
    # Timestamps
    if "onboarding_date" in df_clean.columns:
        ts_df = clean_timestamp_series(df_clean["onboarding_date"], "onboarding_date")
        df_clean = pd.concat([df_clean, ts_df], axis=1)
        
    # Settlement account
    if "settlement_account" in df_clean.columns:
        df_clean["settlement_account_missing"] = df_clean["settlement_account"].isna() | (df_clean["settlement_account"].astype(str).str.strip().isin(["", "NA", "N/A", "None", "null"]))
        df_clean["settlement_account_invalid"] = (~df_clean["settlement_account_missing"]) & (~df_clean["settlement_account"].astype(str).str.isalnum())
        
    # Categoricals
    if "merchant_status" in df_clean.columns:
        df_clean["merchant_status_raw"] = df_clean["merchant_status"]
        df_clean["merchant_status_clean"] = df_clean["merchant_status"].apply(normalize_merchant_status)
        
    for col in ["merchant_category", "business_type"]:
        if col in df_clean.columns:
            df_clean[f"{col}_clean"] = df_clean[col].apply(canonicalize_generic)
            
    for col in ["city", "state"]:
        if col in df_clean.columns:
            df_clean[f"{col}_clean"] = df_clean[col].astype(str).str.strip().str.title()
            
    df_clean["source_dataset"] = "track1_merchants_master"
    df_clean["source_row_number"] = df_clean.index.astype(str)
    
    stats["processed_rows"] = len(df_clean)
    
    return df_clean, stats
