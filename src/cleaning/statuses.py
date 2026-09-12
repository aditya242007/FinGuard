"""
Status Normalization Helpers.
"""
from __future__ import annotations
import pandas as pd

def normalize_txn_status(raw: str) -> str:
    """Normalize transaction status to SUCCESS, FAILED, PENDING, or UNKNOWN."""
    if not raw or pd.isna(raw):
        return "UNKNOWN"
        
    upper = str(raw).strip().upper()
    
    if upper in ("SUCCESS", "TXN_SUCCESS", "COMPLETED", "S"):
        return "SUCCESS"
    if upper in ("FAILED", "TXN_FAILED", "FAIL", "DECLINED", "F"):
        return "FAILED"
    if upper in ("PENDING", "PROCESSING", "INITIATED"):
        return "PENDING"
        
    return upper

def normalize_kyc_status(raw: str) -> str:
    """Normalize KYC status to VERIFIED, PENDING, REJECTED, or UNKNOWN."""
    if not raw or pd.isna(raw):
        return "UNKNOWN"
        
    upper = str(raw).strip().upper()
    
    if upper in ("VERIFIED", "DONE", "APPROVED", "V"):
        return "VERIFIED"
    if upper in ("PENDING", "IN_PROGRESS", "P"):
        return "PENDING"
    if upper in ("REJECTED", "FAILED", "R"):
        return "REJECTED"
        
    return upper

def normalize_merchant_status(raw: str) -> str:
    """Normalize merchant status to ACTIVE, INACTIVE, SUSPENDED, or UNKNOWN."""
    if not raw or pd.isna(raw):
        return "UNKNOWN"
        
    upper = str(raw).strip().upper()
    
    if upper in ("ACTIVE", "A"):
        return "ACTIVE"
    if upper in ("INACTIVE", "I"):
        return "INACTIVE"
    if upper in ("SUSPENDED", "S", "BLOCKED"):
        return "SUSPENDED"
        
    return upper

def canonicalize_generic(raw: str) -> str:
    """Generic uppercase and strip for things like severity, channel, reason codes."""
    if not raw or pd.isna(raw):
        return ""
    return str(raw).strip().upper()
