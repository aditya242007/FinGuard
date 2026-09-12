"""
tests/test_audit.py
-------------------
Pytest test suite for FinGuard Milestone 1.

Tests cover:
1. ID normalization helpers (user, merchant, txn)
2. Amount anomaly detection (currency symbols, 'k' suffix, negative, zero, malformed)
3. Duplicate detection (keys and complete rows)
4. Missing value detection
5. Full report generation (JSON + Markdown)
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest

from src.quality.audit import (
    normalize_user_id,
    normalize_merchant_id,
    normalize_txn_id,
    parse_amount,
    detect_amount_anomalies,
    classify_timestamp,
    classify_mcc,
    profile_dataset,
    audit_transactions,
    audit_kyc,
    audit_merchants,
    audit_chargebacks,
    audit_referential_integrity,
    run_full_audit,
)
from src.quality.report import generate_reports


# ---------------------------------------------------------------------------
# 1. ID Normalization Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("USR12345", "12345"),
        ("usr12345", "12345"),
        ("USR-12345", "12345"),
        ("USR 12345", "12345"),
        ("usr_12345", "12345"),
        ("12345", "12345"),
        ("USR00012345", "12345"),
        ("INVALID_USER", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_user_id(raw, expected):
    assert normalize_user_id(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MCH1234", "1234"),
        ("mch1234", "1234"),
        ("MCH-1234", "1234"),
        ("MCH 1234", "1234"),
        ("mch_1234", "1234"),
        ("1234", "1234"),
        ("MCH001234", "1234"),
        ("BAD_MERCHANT", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_merchant_id(raw, expected):
    assert normalize_merchant_id(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("TXN00001234", "1234"),
        ("txn-1234", "1234"),
        ("TXN 1234", "1234"),
        ("1234", "1234"),
        ("TXN_9999", "9999"),
        ("NOT_A_TXN", None),
    ],
)
def test_normalize_txn_id(raw, expected):
    assert normalize_txn_id(raw) == expected


# ---------------------------------------------------------------------------
# 2. Amount Anomaly Detection Tests
# ---------------------------------------------------------------------------

def test_parse_amount_various_formats():
    assert parse_amount("15722.34") == 15722.34
    assert parse_amount("Rs. 6362.9") == 6362.9
    assert parse_amount("₹11,214") == 11214.0
    assert parse_amount("INR 2,432.18") == 2432.18
    assert parse_amount("27.3k") == 27300.0
    assert parse_amount("-1271.48") == -1271.48
    assert parse_amount("0") == 0.0
    assert parse_amount("invalid_amount") is None
    assert parse_amount("") is None


def test_detect_amount_anomalies():
    s = pd.Series(["100.50", "Rs. 200", "-50.0", "0", "", "invalid", "₹1,000"])
    anomalies = detect_amount_anomalies(s)
    
    assert anomalies["blank_count"] == 1
    assert anomalies["malformed_count"] == 1
    assert anomalies["negative_count"] == 1
    assert anomalies["zero_count"] == 1
    assert anomalies["valid_count"] == 3


# ---------------------------------------------------------------------------
# 3. Duplicate Detection Tests
# ---------------------------------------------------------------------------

def test_duplicate_detection_profile():
    df = pd.DataFrame({
        "col1": ["A", "B", "A", "C"],
        "col2": ["1", "2", "1", "3"],
    })
    prof = profile_dataset(df, "test_dataset")
    assert prof["row_count"] == 4
    assert prof["duplicate_row_count"] == 1


def test_duplicate_txn_ids():
    df = pd.DataFrame({
        "txn_id": ["TXN1", "TXN2", "TXN1", "TXN3"],
        "user_id": ["USR1", "USR2", "USR3", "USR4"],
        "merchant_id": ["MCH1", "MCH2", "MCH3", "MCH4"],
        "amount": ["100", "200", "300", "400"],
        "utr": ["UTR1", "UTR2", "UTR3", "UTR4"],
        "mcc": ["5411", "5411", "5411", "5411"],
        "status": ["SUCCESS", "FAILED", "SUCCESS", "PENDING"],
    })
    issues = audit_transactions(df)
    assert issues["duplicate_txn_id"]["count"] == 2


# ---------------------------------------------------------------------------
# 4. Missing Value Detection Tests
# ---------------------------------------------------------------------------

def test_missing_value_detection():
    df = pd.DataFrame({
        "txn_id": ["TXN1", ""],
        "user_id": ["", " "],
        "merchant_id": ["MCH1", "MCH2"],
        "amount": ["100", "200"],
        "utr": ["", "UTR2"],
        "mcc": ["5411", ""],
        "status": ["S", "F"],
    })
    issues = audit_transactions(df)
    assert issues["blank_txn_id"]["count"] == 1
    assert issues["blank_user_id"]["count"] == 2
    assert issues["blank_utr"]["count"] == 1


# ---------------------------------------------------------------------------
# 5. Report Generation Tests
# ---------------------------------------------------------------------------

def test_generate_reports(tmp_path: Path):
    txn_df = pd.DataFrame({
        "txn_id": ["TXN1", "TXN2"],
        "user_id": ["USR1", "USR2"],
        "merchant_id": ["MCH1", "MCH2"],
        "amount": ["100.0", "Rs. 200"],
        "utr": ["UTR1", "UTR2"],
        "mcc": ["5411", "05411"],
        "timestamp": ["2026-01-01 10:00:00", "1770063471"],
        "status": ["COMPLETED", "FAILED"],
    })
    kyc_df = pd.DataFrame({
        "user_id": ["USR1", "usr2"],
        "full_name": ["Alice", "Bob"],
        "pan": ["ABCDE1234F", ""],
        "aadhaar": ["1234 5678 9012", "987654321098"],
        "date_of_birth": ["1990-01-01", ""],
        "city": ["delhi", "Mumbai"],
        "state": ["Delhi", "Maharashtra"],
        "monthly_income": ["50000", "₹20,000"],
        "occupation": ["Engineer", "Teacher"],
        "signup_timestamp": ["2025-01-01", "2025-02-01"],
        "kyc_status": ["VERIFIED", "Pending"],
        "risk_segment": ["low", "HIGH"],
    })
    merchant_df = pd.DataFrame({
        "merchant_id": ["MCH1", "mch2"],
        "merchant_name": ["Store A", "Store B"],
        "mcc": ["5411", "MCC-7011"],
        "merchant_category": ["Retail", "hotel_lodging"],
        "business_type": ["Proprietorship", "Private Limited"],
        "city": ["Delhi", "Mumbai"],
        "state": ["Delhi", "Maharashtra"],
        "onboarding_date": ["2024-01-01", "09-23-2025"],
        "settlement_account": ["1234567890", "NA"],
        "merchant_status": ["ACTIVE", "Inactive"],
        "declared_avg_ticket_size": ["1000", "-500"],
    })
    cb_df = pd.DataFrame({
        "complaint_id": ["CBK1", "CBK2"],
        "txn_id": ["TXN1", ""],
        "user_id": ["USR1", "USR999"],
        "merchant_id": ["MCH1", "MCH999"],
        "disputed_amount": ["100", ""],
        "reason_code": ["Fraud", "fraud"],
        "resolution_status": ["OPEN", "closed"],
        "severity": ["High", "LOW"],
        "channel": ["web", "App"],
        "transaction_timestamp": ["2026-01-01", "1772691855"],
        "reported_timestamp": ["2026-01-02", "2026-01-03"],
        "bank_response_timestamp": ["2026-01-05", "2026-01-06"],
    })

    audit_result = run_full_audit(txn_df, kyc_df, merchant_df, cb_df)
    reports_dir = tmp_path / "reports"
    
    json_path, md_path = generate_reports(audit_result, reports_dir)
    
    assert json_path.exists()
    assert md_path.exists()
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "transactions" in data
        assert "referential_integrity" in data

    md_content = md_path.read_text(encoding="utf-8")
    assert "# FinGuard Data Quality Report" in md_content
    assert "## Executive Summary" in md_content
    assert "## Recommended Cleaning Actions" in md_content
