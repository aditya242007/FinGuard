"""
UTR Cleaning Helpers.
"""
from __future__ import annotations
import pandas as pd

def clean_utr(raw: str) -> str:
    if not raw or pd.isna(raw):
        return ""
    return str(raw).strip().replace(" ", "").replace("-", "").upper()

def clean_utr_series(series: pd.Series) -> pd.DataFrame:
    clean_series = series.apply(clean_utr)
    missing = clean_series == ""
    # simple check: if it doesn't look like a standard length alphanumeric after stripping
    # Real UTRs in UPI are typically 12 digits, but we just check if it's alphanumeric and len >= 8 as a proxy
    invalid = (~missing) & (~clean_series.str.isalnum() | (clean_series.str.len() < 8))
    
    return pd.DataFrame({
        "utr_clean": clean_series,
        "utr_missing": missing,
        "utr_invalid": invalid,
    })
