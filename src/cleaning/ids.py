"""
ID Normalization helpers.
"""
from __future__ import annotations
import re
import pandas as pd

_USR_RE = re.compile(r"^(?:USR[-_\s]?)?(\d+)$", re.IGNORECASE)
_MCH_RE = re.compile(r"^(?:MCH[-_\s]?)?(\d+)$", re.IGNORECASE)
_TXN_RE = re.compile(r"^(?:TXN[-_\s]?)?(\d+)$", re.IGNORECASE)

def normalize_user_id(raw: str) -> str:
    """Normalize user ID to USRXXXX format or keep original if unparseable."""
    if not raw or pd.isna(raw):
        return ""
    raw = str(raw).strip()
    m = _USR_RE.match(raw)
    if m:
        num = m.group(1).lstrip("0") or "0"
        return f"USR{num}"
    return raw

def normalize_merchant_id(raw: str) -> str:
    """Normalize merchant ID to MCHXXXX format or keep original if unparseable."""
    if not raw or pd.isna(raw):
        return ""
    raw = str(raw).strip()
    m = _MCH_RE.match(raw)
    if m:
        num = m.group(1).lstrip("0") or "0"
        return f"MCH{num}"
    return raw

def normalize_txn_id(raw: str) -> str:
    """Normalize txn ID to TXNXXXX format conservatively."""
    if not raw or pd.isna(raw):
        return ""
    raw = str(raw).strip()
    m = _TXN_RE.match(raw)
    if m:
        num = m.group(1).lstrip("0") or "0"
        return f"TXN{num.zfill(8)}" # Standardize length if possible, or just prepend TXN
    # The requirement says "normalize case/whitespace/separators conservatively"
    # Let's just strip whitespace and uppercase for TXN IDs if they don't match the regex nicely
    return raw.upper().replace(" ", "").replace("-", "").replace("_", "")

def normalize_complaint_id(raw: str) -> str:
    if not raw or pd.isna(raw):
        return ""
    return str(raw).strip().upper()
