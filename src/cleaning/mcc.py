"""
MCC Normalization Helpers.
"""
from __future__ import annotations
import re
import pandas as pd

_MCC_STANDARD = re.compile(r"^\d{4}$")
_MCC_PREFIXED = re.compile(r"^0(\d{4})$")
_MCC_DASHED = re.compile(r"^MCC-(\d{4})$", re.IGNORECASE)

def normalize_mcc(raw: str) -> str:
    if not raw or pd.isna(raw):
        return ""
    
    raw_str = str(raw).strip()
    
    m_dashed = _MCC_DASHED.match(raw_str)
    if m_dashed:
        return m_dashed.group(1)
        
    m_prefixed = _MCC_PREFIXED.match(raw_str)
    if m_prefixed:
        return m_prefixed.group(1)
        
    if _MCC_STANDARD.match(raw_str):
        return raw_str
        
    return raw_str

def clean_mcc_series(series: pd.Series) -> pd.DataFrame:
    clean_series = series.apply(normalize_mcc)
    missing = clean_series == ""
    return pd.DataFrame({
        "mcc_clean": clean_series,
        "mcc_missing": missing,
    })
