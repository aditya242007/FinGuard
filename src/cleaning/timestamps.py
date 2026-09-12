"""
Timestamp Normalization Helpers.
"""
from __future__ import annotations
import pandas as pd
import re

_UNIX_EPOCH_RE = re.compile(r"^\d{9,11}$")

def parse_timestamp(raw: str) -> pd.Timestamp | pd.NaT:
    if not raw or pd.isna(raw):
        return pd.NaT
    
    raw_str = str(raw).strip()
    if not raw_str:
        return pd.NaT
        
    if _UNIX_EPOCH_RE.match(raw_str):
        try:
            return pd.to_datetime(int(raw_str), unit='s')
        except (ValueError, OverflowError):
            pass
            
    formats_to_try = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%m/%d/%Y %I:%M %p",
        "%d/%m/%Y %I:%M %p",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
    ]
    
    for fmt in formats_to_try:
        try:
            # We strictly try formats to avoid silent weird coercions
            parsed = pd.to_datetime(raw_str, format=fmt)
            return parsed
        except (ValueError, TypeError):
            continue
            
    try:
        # Fallback to dateutil parser if explicit formats fail, but cautiously
        parsed = pd.to_datetime(raw_str)
        return parsed
    except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime):
        return pd.NaT

def clean_timestamp_series(series: pd.Series, prefix: str) -> pd.DataFrame:
    """
    Cleans a timestamp series and returns a DataFrame with:
    - {prefix}_clean
    - {prefix}_missing
    - {prefix}_parse_failed
    - {prefix}_was_epoch
    """
    missing_mask = series.isna() | (series.astype(str).str.strip() == "")
    was_epoch_mask = series.astype(str).str.strip().str.match(r"^\d{9,11}$") & ~missing_mask
    
    clean_series = series.apply(parse_timestamp)
    parse_failed_mask = clean_series.isna() & ~missing_mask
    
    return pd.DataFrame({
        f"{prefix}_clean": clean_series,
        f"{prefix}_missing": missing_mask,
        f"{prefix}_parse_failed": parse_failed_mask,
        f"{prefix}_was_epoch": was_epoch_mask,
    })
