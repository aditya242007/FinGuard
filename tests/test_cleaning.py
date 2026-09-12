"""
Pytest suite for cleaning functions.
"""
from __future__ import annotations
import pytest
import pandas as pd
import numpy as np

from src.cleaning.ids import normalize_user_id, normalize_merchant_id, normalize_txn_id
from src.cleaning.amounts import parse_amount, clean_amount_series
from src.cleaning.timestamps import parse_timestamp, clean_timestamp_series
from src.cleaning.statuses import normalize_txn_status, normalize_kyc_status, normalize_merchant_status
from src.cleaning.utr import clean_utr
from src.cleaning.mcc import normalize_mcc

def test_normalize_user_id():
    assert normalize_user_id("USR12345") == "USR12345"
    assert normalize_user_id("usr12345") == "USR12345"
    assert normalize_user_id("USR-12345") == "USR12345"
    assert normalize_user_id("USR 12345") == "USR12345"
    assert normalize_user_id("usr_12345") == "USR12345"
    assert normalize_user_id("12345") == "USR12345"
    
def test_normalize_merchant_id():
    assert normalize_merchant_id("MCH1234") == "MCH1234"
    assert normalize_merchant_id("mch1234") == "MCH1234"
    assert normalize_merchant_id("MCH-1234") == "MCH1234"
    assert normalize_merchant_id("MCH 1234") == "MCH1234"
    assert normalize_merchant_id("1234") == "MCH1234"
    
def test_normalize_txn_id():
    assert normalize_txn_id("TXN1234") == "TXN00001234"
    assert normalize_txn_id("txn-1234") == "TXN00001234"
    assert normalize_txn_id("1234") == "TXN00001234"
    
def test_parse_amount():
    assert parse_amount("15722.34") == 15722.34
    assert parse_amount("Rs. 6362.9") == 6362.9
    assert parse_amount("₹1,234.50") == 1234.5
    assert parse_amount("INR 5000") == 5000.0
    assert parse_amount("50k") == 50000.0
    assert parse_amount("-100.5") == -100.5
    assert np.isnan(parse_amount("invalid"))
    assert np.isnan(parse_amount(""))
    
def test_parse_timestamp():
    assert not pd.isna(parse_timestamp("2026-01-15 00:11:30"))
    assert not pd.isna(parse_timestamp("1770063471"))  # Epoch
    assert not pd.isna(parse_timestamp("06/04/1967 12:14 AM"))
    assert pd.isna(parse_timestamp("invalid_date"))

def test_normalize_txn_status():
    assert normalize_txn_status("Success") == "SUCCESS"
    assert normalize_txn_status("S") == "SUCCESS"
    assert normalize_txn_status("Fail") == "FAILED"
    assert normalize_txn_status("F") == "FAILED"
    assert normalize_txn_status("Pending") == "PENDING"
    
def test_normalize_kyc_status():
    assert normalize_kyc_status("V") == "VERIFIED"
    assert normalize_kyc_status("P") == "PENDING"
    assert normalize_kyc_status("R") == "REJECTED"
    
def test_clean_utr():
    assert clean_utr(" UTR-123 ") == "UTR123"
    
def test_normalize_mcc():
    assert normalize_mcc("5411") == "5411"
    assert normalize_mcc("05411") == "5411"
    assert normalize_mcc("MCC-5411") == "5411"
