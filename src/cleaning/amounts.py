"""
Amount Cleaning Helpers.
"""
from __future__ import annotations
import re
import pandas as pd
import numpy as np

_AMOUNT_STRIP_RE = re.compile(r"[₹$]|Rs\.?\s*|INR\s*|,", re.IGNORECASE)

def parse_amount(raw: str) -> float | np.nan:
    if not raw or pd.isna(raw):
        return np.nan
    raw_str = str(raw).strip()
    if not raw_str:
        return np.nan
    
    cleaned = _AMOUNT_STRIP_RE.sub("", raw_str)
    
    multiplier = 1.0
    if cleaned.lower().endswith("k"):
        multiplier = 1000.0
        cleaned = cleaned[:-1]
        
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return np.nan

def clean_amount_series(series: pd.Series, prefix: str) -> pd.DataFrame:
    """
    Cleans an amount series and returns a DataFrame with:
    - {prefix}_numeric
    - {prefix}_is_negative
    - {prefix}_is_zero
    - {prefix}_parse_failed
    - {prefix}_missing
    """
    numeric_series = series.apply(parse_amount)
    
    missing_mask = series.isna() | (series.astype(str).str.strip() == "")
    parse_failed_mask = numeric_series.isna() & ~missing_mask
    
    is_negative = (numeric_series < 0).fillna(False)
    is_zero = (numeric_series == 0).fillna(False)
    
    return pd.DataFrame({
        f"{prefix}_numeric": numeric_series,
        f"{prefix}_missing": missing_mask,
        f"{prefix}_parse_failed": parse_failed_mask,
        f"{prefix}_is_negative": is_negative,
        f"{prefix}_is_zero": is_zero,
    })
