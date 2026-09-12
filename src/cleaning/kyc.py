"""
KYC Cleaning.
"""
from __future__ import annotations
import pandas as pd
from src.cleaning.ids import normalize_user_id
from src.cleaning.amounts import clean_amount_series
from src.cleaning.timestamps import clean_timestamp_series
from src.cleaning.statuses import normalize_kyc_status, canonicalize_generic

def clean_kyc(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean KYC dataset."""
    df_clean = df.copy()
    stats = {"raw_rows": len(df)}
    
    dup_mask = df_clean.duplicated(keep="first")
    stats["exact_duplicates_removed"] = int(dup_mask.sum())
    df_clean = df_clean[~dup_mask].copy()
    
    # ID Normalization
    df_clean["original_user_id"] = df_clean["user_id"]
    df_clean["user_id_normalized"] = df_clean["user_id"].apply(normalize_user_id)
    
    # Duplicate grouping
    # Since we can't delete, we assign a duplicate group ID
    df_clean["user_duplicate_group"] = df_clean.groupby("user_id_normalized").ngroup()
    
    # Timestamps
    if "signup_timestamp" in df_clean.columns:
        ts_df = clean_timestamp_series(df_clean["signup_timestamp"], "signup_timestamp")
        df_clean = pd.concat([df_clean, ts_df], axis=1)
        
    if "date_of_birth" in df_clean.columns:
        dob_df = clean_timestamp_series(df_clean["date_of_birth"], "date_of_birth")
        df_clean = pd.concat([df_clean, dob_df], axis=1)
        
    # Amounts
    if "monthly_income" in df_clean.columns:
        inc_df = clean_amount_series(df_clean["monthly_income"], "monthly_income")
        df_clean = pd.concat([df_clean, inc_df], axis=1)
        # We need to map income_missing/parse_failed according to requirements
        df_clean["income_missing"] = df_clean["monthly_income_missing"]
        df_clean["income_parse_failed"] = df_clean["monthly_income_parse_failed"]
        
    # Statuses & categorical
    if "kyc_status" in df_clean.columns:
        df_clean["kyc_status_raw"] = df_clean["kyc_status"]
        df_clean["kyc_status_clean"] = df_clean["kyc_status"].apply(normalize_kyc_status)
        
    if "risk_segment" in df_clean.columns:
        df_clean["risk_segment_clean"] = df_clean["risk_segment"].apply(canonicalize_generic)
        
    # Text normalization
    if "pan" in df_clean.columns:
        df_clean["pan_clean"] = df_clean["pan"].astype(str).str.strip().str.upper()
        
    if "aadhaar" in df_clean.columns:
        df_clean["aadhaar_clean"] = df_clean["aadhaar"].astype(str).str.replace(r"\s+", "", regex=True)
        
    for col in ["city", "state", "occupation"]:
        if col in df_clean.columns:
            df_clean[f"{col}_clean"] = df_clean[col].astype(str).str.strip().str.title()
            
    df_clean["source_dataset"] = "track1_kyc_records"
    df_clean["source_row_number"] = df_clean.index.astype(str)
    
    stats["processed_rows"] = len(df_clean)
    
    return df_clean, stats
