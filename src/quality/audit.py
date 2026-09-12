"""
src/quality/audit.py
--------------------
Data Audit / Data Quality Engine — Milestone 1.

Philosophy:
- AUDIT ONLY. No values are modified, imputed, or deleted here.
- Every finding is returned as a structured dict for report generation.
- Functions are modular and individually testable.
- No hardcoded row counts or expected categories.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1 — Generic dataset profile
# ============================================================================

def profile_dataset(df: pd.DataFrame, name: str) -> dict[str, Any]:
    """Produce a generic quality profile for any DataFrame.

    Returns row/column counts, column names, per-column missing values,
    unique counts, duplicate row count, and sample + numeric stats.

    Parameters
    ----------
    df : pd.DataFrame
        The dataset to profile (all-string columns expected).
    name : str
        Human-readable dataset name for logging / reporting.

    Returns
    -------
    dict
        Profile dict suitable for inclusion in the final JSON report.
    """
    logger.info("Profiling dataset: %s (%d rows)", name, len(df))

    total_rows = len(df)
    total_cols = len(df.columns)

    # --- Missing values (treat empty strings as missing) -------------------
    def _is_blank(series: pd.Series) -> pd.Series:
        return series.apply(lambda v: v is None or str(v).strip() == "")

    missing_info: list[dict] = []
    for col in df.columns:
        blank_mask = _is_blank(df[col])
        missing_count = int(blank_mask.sum())
        pct = round(missing_count / total_rows * 100, 2) if total_rows > 0 else 0.0
        unique_count = int(df[col].nunique())
        sample = [
            str(v) for v in df[col][~blank_mask].dropna().head(5).tolist()
        ]
        missing_info.append(
            {
                "column": col,
                "dtype": str(df[col].dtype),
                "missing_count": missing_count,
                "missing_pct": pct,
                "unique_count": unique_count,
                "sample_values": sample,
            }
        )

    # --- Duplicate rows ----------------------------------------------------
    dup_row_count = int(df.duplicated().sum())

    # --- Numeric stats for columns that look numeric -----------------------
    numeric_stats: dict[str, Any] = {}
    for col in df.columns:
        cleaned = (
            df[col]
            .str.replace(r"[₹$,\s]", "", regex=True)
            .str.replace(r"Rs\.?\s*", "", regex=True, flags=re.IGNORECASE)
            .str.replace(r"INR\s*", "", regex=True, flags=re.IGNORECASE)
        )
        numeric_series = pd.to_numeric(cleaned, errors="coerce")
        valid = numeric_series.dropna()
        if len(valid) >= 0.5 * total_rows and len(valid) > 0:
            numeric_stats[col] = {
                "mean": round(float(valid.mean()), 4),
                "median": round(float(valid.median()), 4),
                "std": round(float(valid.std()), 4),
                "min": round(float(valid.min()), 4),
                "max": round(float(valid.max()), 4),
                "negative_count": int((valid < 0).sum()),
                "zero_count": int((valid == 0).sum()),
            }

    return {
        "dataset": name,
        "row_count": total_rows,
        "column_count": total_cols,
        "column_names": list(df.columns),
        "missing_values": missing_info,
        "duplicate_row_count": dup_row_count,
        "numeric_stats": numeric_stats,
    }


# ============================================================================
# SECTION 2 — ID Normalisation Helpers (audit-only, no overwriting)
# ============================================================================

_USR_RE = re.compile(
    r"^(?:USR[-_\s]?)?(\d+)$", re.IGNORECASE
)
_MCH_RE = re.compile(
    r"^(?:MCH[-_\s]?)?(\d+)$", re.IGNORECASE
)
_TXN_RE = re.compile(
    r"^(?:TXN[-_\s]?)?(\d+)$", re.IGNORECASE
)


def normalize_user_id(raw: str) -> str | None:
    """Extract the numeric core from a user ID, if recognisable.

    Handles: USR12345, usr12345, USR-12345, USR 12345, usr_12345, 12345.

    Returns the zero-padded numeric string (e.g., '12345') or None if
    the value does not match any known pattern.

    NOTE: This function is for audit / matching purposes only.
    It does NOT modify any stored data.
    """
    if not raw or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    m = _USR_RE.match(stripped)
    if m:
        return m.group(1).lstrip("0") or "0"
    return None


def normalize_merchant_id(raw: str) -> str | None:
    """Extract the numeric core from a merchant ID, if recognisable.

    Handles: MCH1234, mch1234, MCH-1234, MCH 1234, 1234.

    Returns the numeric string or None if unrecognised.
    """
    if not raw or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    m = _MCH_RE.match(stripped)
    if m:
        return m.group(1).lstrip("0") or "0"
    return None


def normalize_txn_id(raw: str) -> str | None:
    """Extract the numeric core from a transaction ID, if recognisable.

    Handles: TXN00001234, txn-1234, 1234, etc.
    """
    if not raw or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    m = _TXN_RE.match(stripped)
    if m:
        return m.group(1).lstrip("0") or "0"
    return None


# ============================================================================
# SECTION 3 — Amount Anomaly Helpers
# ============================================================================

_AMOUNT_STRIP_RE = re.compile(
    r"[₹$]|Rs\.?\s*|INR\s*|,", re.IGNORECASE
)


def parse_amount(raw: str) -> float | None:
    """Attempt to parse a raw amount string into a float.

    Strips currency symbols (₹, $, Rs., INR) and thousands commas.
    Returns None if the result is not a valid number.
    """
    if not raw or not isinstance(raw, str):
        return None
    cleaned = _AMOUNT_STRIP_RE.sub("", raw.strip())
    # Handle k/K suffix (e.g. 27.3k)
    if cleaned.lower().endswith("k"):
        try:
            return float(cleaned[:-1]) * 1_000
        except ValueError:
            return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def detect_amount_anomalies(series: pd.Series) -> dict[str, Any]:
    """Detect anomalies in a raw amount column.

    Returns counts for: blank, malformed (unparseable), negative, zero,
    and an overall statistics snapshot.
    """
    blank_mask = series.apply(lambda v: str(v).strip() == "")
    non_blank = series[~blank_mask]

    parsed = non_blank.apply(parse_amount)
    malformed_mask = parsed.isna()
    malformed_count = int(malformed_mask.sum())
    malformed_examples = non_blank[malformed_mask].head(10).tolist()

    valid = parsed.dropna()
    negative_count = int((valid < 0).sum())
    zero_count = int((valid == 0).sum())

    return {
        "blank_count": int(blank_mask.sum()),
        "malformed_count": malformed_count,
        "malformed_examples": malformed_examples,
        "negative_count": negative_count,
        "zero_count": zero_count,
        "valid_count": int((~malformed_mask).sum()) - zero_count - negative_count,
        "stats": {
            "mean": round(float(valid.mean()), 4) if len(valid) > 0 else None,
            "min": round(float(valid.min()), 4) if len(valid) > 0 else None,
            "max": round(float(valid.max()), 4) if len(valid) > 0 else None,
        },
    }


# ============================================================================
# SECTION 4 — Timestamp Helpers
# ============================================================================

_UNIX_EPOCH_RE = re.compile(r"^\d{9,11}$")


def classify_timestamp(raw: str) -> str:
    """Classify a raw timestamp string by format type.

    Returns one of:
        'blank', 'unix_epoch', 'iso8601', 'date_only', 'mixed_format',
        'unparseable'
    """
    if not raw or str(raw).strip() == "":
        return "blank"
    s = str(raw).strip()
    if _UNIX_EPOCH_RE.match(s):
        return "unix_epoch"
    # Try a broad parse
    formats = [
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
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            pd.to_datetime(s, format=fmt)
            if " " in s or "T" in s:
                return "iso8601"
            return "date_only"
        except (ValueError, TypeError):
            continue
    # Try pandas flexible parser as a last resort
    try:
        pd.to_datetime(s, infer_datetime_format=True)
        return "mixed_format"
    except (ValueError, TypeError):
        return "unparseable"


def detect_timestamp_anomalies(series: pd.Series) -> dict[str, Any]:
    """Classify every value in a timestamp column and count by category."""
    classifications = series.apply(classify_timestamp)
    counts = classifications.value_counts().to_dict()
    return {
        "blank": counts.get("blank", 0),
        "unix_epoch": counts.get("unix_epoch", 0),
        "iso8601": counts.get("iso8601", 0),
        "date_only": counts.get("date_only", 0),
        "mixed_format": counts.get("mixed_format", 0),
        "unparseable": counts.get("unparseable", 0),
        "examples": {
            k: series[classifications == k].head(3).tolist()
            for k in counts
        },
    }


# ============================================================================
# SECTION 5 — MCC Helpers
# ============================================================================

_MCC_STANDARD = re.compile(r"^\d{4}$")
_MCC_PREFIXED = re.compile(r"^0\d{4}$")          # 05411 → leading zero
_MCC_DASHED   = re.compile(r"^MCC-\d{4}$", re.IGNORECASE)


def classify_mcc(raw: str) -> str:
    """Classify an MCC value by format.

    Returns: 'standard', 'leading_zero', 'dashed_prefix',
             'blank', or 'unusual'.
    """
    if not raw or str(raw).strip() == "":
        return "blank"
    s = str(raw).strip()
    if _MCC_STANDARD.match(s):
        return "standard"
    if _MCC_PREFIXED.match(s):
        return "leading_zero"
    if _MCC_DASHED.match(s):
        return "dashed_prefix"
    return "unusual"


# ============================================================================
# SECTION 6 — Dataset-Specific Audits
# ============================================================================

def audit_transactions(df: pd.DataFrame) -> dict[str, Any]:
    """Audit the UPI transactions dataset.

    Detects: duplicate txn_id, duplicate rows, missing key fields,
    amount anomalies, timestamp anomalies, MCC format issues,
    and all distinct status values.
    """
    logger.info("Running transaction-specific audit (%d rows)", len(df))
    total = len(df)

    issues: dict[str, Any] = {}

    # ---- Duplicate txn_id -------------------------------------------------
    dup_txn_mask = df["txn_id"].duplicated(keep=False)
    issues["duplicate_txn_id"] = {
        "count": int(dup_txn_mask.sum()),
        "examples": df.loc[dup_txn_mask, "txn_id"].head(5).tolist(),
    }

    # ---- Duplicate complete rows ------------------------------------------
    dup_rows = int(df.duplicated().sum())
    issues["duplicate_complete_rows"] = {"count": dup_rows}

    # ---- Missing / blank key fields ---------------------------------------
    for field in ["txn_id", "user_id", "merchant_id", "utr"]:
        if field not in df.columns:
            issues[f"missing_column_{field}"] = {"count": total}
            continue
        blank_mask = df[field].apply(lambda v: str(v).strip() == "")
        issues[f"blank_{field}"] = {
            "count": int(blank_mask.sum()),
            "pct": round(blank_mask.sum() / total * 100, 2),
        }

    # ---- Amount anomalies -------------------------------------------------
    if "amount" in df.columns:
        issues["amount_anomalies"] = detect_amount_anomalies(df["amount"])

    # ---- Timestamp anomalies ----------------------------------------------
    if "timestamp" in df.columns:
        issues["timestamp_anomalies"] = detect_timestamp_anomalies(df["timestamp"])

    # ---- MCC format issues ------------------------------------------------
    if "mcc" in df.columns:
        mcc_classes = df["mcc"].apply(classify_mcc)
        mcc_counts = mcc_classes.value_counts().to_dict()
        issues["mcc_format"] = {
            "counts": mcc_counts,
            "unusual_examples": df.loc[mcc_classes == "unusual", "mcc"].head(5).tolist(),
        }

    # ---- Status values ----------------------------------------------------
    if "status" in df.columns:
        status_counts = df["status"].value_counts(dropna=False).to_dict()
        issues["status_distribution"] = {str(k): int(v) for k, v in status_counts.items()}

    return issues


def audit_kyc(df: pd.DataFrame) -> dict[str, Any]:
    """Audit the KYC records dataset.

    Detects: duplicate user IDs, duplicate rows, missing PAN/Aadhaar/DOB/
    income/signup, inconsistent KYC status and risk segment values,
    city/state capitalisation inconsistencies, suspicious income formats.
    """
    logger.info("Running KYC-specific audit (%d rows)", len(df))
    total = len(df)
    issues: dict[str, Any] = {}

    # ---- Duplicate user_id -----------------------------------------------
    if "user_id" in df.columns:
        norm_ids = df["user_id"].apply(normalize_user_id)
        dup_id_mask = norm_ids.duplicated(keep=False) & norm_ids.notna()
        issues["duplicate_user_id_normalised"] = {
            "count": int(dup_id_mask.sum()),
            "raw_examples": df.loc[dup_id_mask, "user_id"].head(5).tolist(),
        }
        raw_dup_mask = df["user_id"].duplicated(keep=False)
        issues["duplicate_user_id_raw"] = {
            "count": int(raw_dup_mask.sum()),
        }

    # ---- Duplicate complete rows ------------------------------------------
    issues["duplicate_complete_rows"] = {"count": int(df.duplicated().sum())}

    # ---- Missing key fields -----------------------------------------------
    for field in ["pan", "aadhaar", "date_of_birth", "monthly_income", "signup_timestamp"]:
        if field not in df.columns:
            issues[f"missing_column_{field}"] = {"count": total}
            continue
        blank_mask = df[field].apply(lambda v: str(v).strip() == "")
        issues[f"blank_{field}"] = {
            "count": int(blank_mask.sum()),
            "pct": round(blank_mask.sum() / total * 100, 2),
        }

    # ---- KYC status values -----------------------------------------------
    if "kyc_status" in df.columns:
        ks_counts = df["kyc_status"].value_counts(dropna=False).to_dict()
        issues["kyc_status_distribution"] = {str(k): int(v) for k, v in ks_counts.items()}
        # Distinct case-insensitive normalised values
        normalised_ks = df["kyc_status"].str.strip().str.upper()
        issues["kyc_status_unique_normalised"] = sorted(normalised_ks.unique().tolist())

    # ---- Risk segment values ---------------------------------------------
    if "risk_segment" in df.columns:
        rs_counts = df["risk_segment"].value_counts(dropna=False).to_dict()
        issues["risk_segment_distribution"] = {str(k): int(v) for k, v in rs_counts.items()}
        issues["risk_segment_unique_normalised"] = sorted(
            df["risk_segment"].str.strip().str.upper().unique().tolist()
        )

    # ---- City/state capitalisation inconsistency -------------------------
    for field in ["city", "state"]:
        if field not in df.columns:
            continue
        non_blank = df[field][df[field].apply(lambda v: str(v).strip() != "")]
        title_count = int(non_blank.apply(lambda v: v == v.title()).sum())
        inconsistent_count = len(non_blank) - title_count
        issues[f"{field}_capitalisation_inconsistencies"] = {
            "total_non_blank": len(non_blank),
            "inconsistent_count": inconsistent_count,
            "examples": non_blank[
                non_blank.apply(lambda v: v != v.title())
            ].head(5).tolist(),
        }

    # ---- Income anomalies ------------------------------------------------
    if "monthly_income" in df.columns:
        issues["income_anomalies"] = detect_amount_anomalies(df["monthly_income"])
        # Flag values with symbols or suffixes
        symbol_mask = df["monthly_income"].str.contains(
            r"[₹$k]|Rs\.|INR", regex=True, case=False, na=False
        )
        issues["income_with_symbols"] = {
            "count": int(symbol_mask.sum()),
            "examples": df.loc[symbol_mask, "monthly_income"].head(10).tolist(),
        }

    # ---- Signup timestamp anomalies --------------------------------------
    if "signup_timestamp" in df.columns:
        issues["signup_timestamp_anomalies"] = detect_timestamp_anomalies(
            df["signup_timestamp"]
        )

    return issues


def audit_merchants(df: pd.DataFrame) -> dict[str, Any]:
    """Audit the merchant master dataset.

    Detects: duplicate merchant IDs, duplicate rows, missing MCC/onboarding/
    settlement account, MCC format issues, inconsistent category/status/
    business_type values, malformed ticket sizes.
    """
    logger.info("Running merchant-specific audit (%d rows)", len(df))
    total = len(df)
    issues: dict[str, Any] = {}

    # ---- Duplicate merchant_id -------------------------------------------
    if "merchant_id" in df.columns:
        norm_ids = df["merchant_id"].apply(normalize_merchant_id)
        dup_norm_mask = norm_ids.duplicated(keep=False) & norm_ids.notna()
        issues["duplicate_merchant_id_normalised"] = {
            "count": int(dup_norm_mask.sum()),
            "raw_examples": df.loc[dup_norm_mask, "merchant_id"].head(5).tolist(),
        }
        raw_dup_mask = df["merchant_id"].duplicated(keep=False)
        issues["duplicate_merchant_id_raw"] = {"count": int(raw_dup_mask.sum())}

    # ---- Duplicate complete rows ------------------------------------------
    issues["duplicate_complete_rows"] = {"count": int(df.duplicated().sum())}

    # ---- MCC format -------------------------------------------------------
    if "mcc" in df.columns:
        blank_mask = df["mcc"].apply(lambda v: str(v).strip() == "")
        issues["blank_mcc"] = {
            "count": int(blank_mask.sum()),
            "pct": round(blank_mask.sum() / total * 100, 2),
        }
        mcc_classes = df["mcc"].apply(classify_mcc)
        mcc_counts = mcc_classes.value_counts().to_dict()
        issues["mcc_format"] = {
            "counts": mcc_counts,
            "unusual_examples": df.loc[mcc_classes == "unusual", "mcc"].head(5).tolist(),
        }

    # ---- Missing onboarding date -----------------------------------------
    if "onboarding_date" in df.columns:
        blank_mask = df["onboarding_date"].apply(lambda v: str(v).strip() == "")
        issues["blank_onboarding_date"] = {
            "count": int(blank_mask.sum()),
            "pct": round(blank_mask.sum() / total * 100, 2),
        }
        issues["onboarding_date_anomalies"] = detect_timestamp_anomalies(
            df["onboarding_date"]
        )

    # ---- Missing settlement account -------------------------------------
    if "settlement_account" in df.columns:
        blank_mask = df["settlement_account"].apply(
            lambda v: str(v).strip() in ("", "NA", "N/A", "None", "null")
        )
        issues["blank_or_invalid_settlement_account"] = {
            "count": int(blank_mask.sum()),
            "pct": round(blank_mask.sum() / total * 100, 2),
            "na_variants": df.loc[
                df["settlement_account"].str.strip().isin(["NA", "N/A", "None", "null"]),
                "settlement_account",
            ].value_counts().to_dict(),
        }

    # ---- Categorical distributions ----------------------------------------
    for field in ["merchant_category", "merchant_status", "business_type"]:
        if field not in df.columns:
            continue
        dist = df[field].value_counts(dropna=False).to_dict()
        issues[f"{field}_distribution"] = {str(k): int(v) for k, v in dist.items()}

    # ---- Ticket size anomalies -------------------------------------------
    if "declared_avg_ticket_size" in df.columns:
        issues["ticket_size_anomalies"] = detect_amount_anomalies(
            df["declared_avg_ticket_size"]
        )

    return issues


def audit_chargebacks(df: pd.DataFrame) -> dict[str, Any]:
    """Audit the chargebacks dataset.

    Detects: duplicate complaint IDs, duplicate txn IDs, blank txn IDs,
    blank/malformed disputed amounts, inconsistent reason codes /
    resolution statuses / severity / channels, malformed timestamps.
    """
    logger.info("Running chargeback-specific audit (%d rows)", len(df))
    total = len(df)
    issues: dict[str, Any] = {}

    # ---- Duplicate complaint_id ------------------------------------------
    if "complaint_id" in df.columns:
        dup_mask = df["complaint_id"].duplicated(keep=False)
        issues["duplicate_complaint_id"] = {
            "count": int(dup_mask.sum()),
            "examples": df.loc[dup_mask, "complaint_id"].head(5).tolist(),
        }

    # ---- Duplicate txn_id -----------------------------------------------
    if "txn_id" in df.columns:
        dup_txn_mask = df["txn_id"].duplicated(keep=False)
        blank_txn_mask = df["txn_id"].apply(lambda v: str(v).strip() == "")
        issues["duplicate_txn_id"] = {
            "count": int(dup_txn_mask.sum()),
            "examples": df.loc[dup_txn_mask, "txn_id"].head(5).tolist(),
        }
        issues["blank_txn_id"] = {
            "count": int(blank_txn_mask.sum()),
            "pct": round(blank_txn_mask.sum() / total * 100, 2),
        }

    # ---- Duplicate complete rows -----------------------------------------
    issues["duplicate_complete_rows"] = {"count": int(df.duplicated().sum())}

    # ---- Disputed amount -------------------------------------------------
    if "disputed_amount" in df.columns:
        issues["disputed_amount_anomalies"] = detect_amount_anomalies(
            df["disputed_amount"]
        )

    # ---- Categorical distributions ---------------------------------------
    for field in ["reason_code", "resolution_status", "severity", "channel"]:
        if field not in df.columns:
            continue
        dist = df[field].value_counts(dropna=False).to_dict()
        issues[f"{field}_distribution"] = {str(k): int(v) for k, v in dist.items()}

    # ---- Timestamp anomalies --------------------------------------------
    for ts_field in ["transaction_timestamp", "reported_timestamp", "bank_response_timestamp"]:
        if ts_field not in df.columns:
            continue
        issues[f"{ts_field}_anomalies"] = detect_timestamp_anomalies(df[ts_field])

    return issues


# ============================================================================
# SECTION 7 — Referential Integrity Audit
# ============================================================================

def _normalise_series(series: pd.Series, fn) -> pd.Series:
    """Apply a normalisation function and return a Series of normalised IDs."""
    return series.apply(fn)


def audit_referential_integrity(
    txn_df: pd.DataFrame,
    kyc_df: pd.DataFrame,
    merchant_df: pd.DataFrame,
    cb_df: pd.DataFrame,
) -> dict[str, Any]:
    """Audit foreign key referential integrity across all four datasets.

    Does NOT assume IDs are clean. Uses normalisation helpers to detect
    matches despite format variants.

    Returns counts and examples of:
    - txn → KYC user_id mismatches
    - txn → merchant_id mismatches
    - chargeback → txn txn_id mismatches
    - chargeback → KYC user_id mismatches
    - chargeback → merchant merchant_id mismatches
    """
    logger.info("Running referential integrity audit")

    def _norm_set(df: pd.DataFrame, col: str, fn) -> set:
        if col not in df.columns:
            return set()
        return {
            n for n in df[col].apply(fn) if n is not None
        }

    # Normalised ID sets
    kyc_user_norm = _norm_set(kyc_df, "user_id", normalize_user_id)
    merch_id_norm = _norm_set(merchant_df, "merchant_id", normalize_merchant_id)
    txn_txn_norm  = _norm_set(txn_df, "txn_id", normalize_txn_id)

    results: dict[str, Any] = {}

    # ---- Transactions → KYC (user_id) ------------------------------------
    if "user_id" in txn_df.columns:
        txn_user_norm = txn_df["user_id"].apply(normalize_user_id)
        txn_blank_user = txn_df["user_id"].apply(lambda v: str(v).strip() == "")

        unmatched_mask = (
            txn_user_norm.apply(lambda n: n not in kyc_user_norm if n else True)
            & ~txn_blank_user
        )
        results["txn_user_not_in_kyc"] = {
            "total_txn": len(txn_df),
            "blank_user_id": int(txn_blank_user.sum()),
            "unmatched_count": int(unmatched_mask.sum()),
            "unmatched_pct": round(unmatched_mask.sum() / len(txn_df) * 100, 2),
            "examples": txn_df.loc[unmatched_mask, "user_id"].head(10).tolist(),
        }

    # ---- Transactions → Merchants (merchant_id) --------------------------
    if "merchant_id" in txn_df.columns:
        txn_merch_norm = txn_df["merchant_id"].apply(normalize_merchant_id)
        txn_blank_merch = txn_df["merchant_id"].apply(lambda v: str(v).strip() == "")

        unmatched_mask = (
            txn_merch_norm.apply(lambda n: n not in merch_id_norm if n else True)
            & ~txn_blank_merch
        )
        results["txn_merchant_not_in_master"] = {
            "total_txn": len(txn_df),
            "blank_merchant_id": int(txn_blank_merch.sum()),
            "unmatched_count": int(unmatched_mask.sum()),
            "unmatched_pct": round(unmatched_mask.sum() / len(txn_df) * 100, 2),
            "examples": txn_df.loc[unmatched_mask, "merchant_id"].head(10).tolist(),
        }

    # ---- Chargebacks → Transactions (txn_id) ----------------------------
    if "txn_id" in cb_df.columns:
        cb_txn_norm = cb_df["txn_id"].apply(normalize_txn_id)
        cb_blank_txn = cb_df["txn_id"].apply(lambda v: str(v).strip() == "")

        unmatched_mask = (
            cb_txn_norm.apply(lambda n: n not in txn_txn_norm if n else True)
            & ~cb_blank_txn
        )
        results["cb_txn_not_in_transactions"] = {
            "total_cb": len(cb_df),
            "blank_txn_id": int(cb_blank_txn.sum()),
            "unmatched_count": int(unmatched_mask.sum()),
            "unmatched_pct": round(unmatched_mask.sum() / len(cb_df) * 100, 2),
            "examples": cb_df.loc[unmatched_mask, "txn_id"].head(10).tolist(),
        }

    # ---- Chargebacks → KYC (user_id) ------------------------------------
    if "user_id" in cb_df.columns:
        cb_user_norm = cb_df["user_id"].apply(normalize_user_id)
        cb_blank_user = cb_df["user_id"].apply(lambda v: str(v).strip() == "")

        unmatched_mask = (
            cb_user_norm.apply(lambda n: n not in kyc_user_norm if n else True)
            & ~cb_blank_user
        )
        results["cb_user_not_in_kyc"] = {
            "total_cb": len(cb_df),
            "blank_user_id": int(cb_blank_user.sum()),
            "unmatched_count": int(unmatched_mask.sum()),
            "unmatched_pct": round(unmatched_mask.sum() / len(cb_df) * 100, 2),
            "examples": cb_df.loc[unmatched_mask, "user_id"].head(10).tolist(),
        }

    # ---- Chargebacks → Merchants (merchant_id) --------------------------
    if "merchant_id" in cb_df.columns:
        cb_merch_norm = cb_df["merchant_id"].apply(normalize_merchant_id)
        cb_blank_merch = cb_df["merchant_id"].apply(lambda v: str(v).strip() == "")

        unmatched_mask = (
            cb_merch_norm.apply(lambda n: n not in merch_id_norm if n else True)
            & ~cb_blank_merch
        )
        results["cb_merchant_not_in_master"] = {
            "total_cb": len(cb_df),
            "blank_merchant_id": int(cb_blank_merch.sum()),
            "unmatched_count": int(unmatched_mask.sum()),
            "unmatched_pct": round(unmatched_mask.sum() / len(cb_df) * 100, 2),
            "examples": cb_df.loc[unmatched_mask, "merchant_id"].head(10).tolist(),
        }

    return results


# ============================================================================
# SECTION 8 — Orchestrator
# ============================================================================

def run_full_audit(
    txn_df: pd.DataFrame,
    kyc_df: pd.DataFrame,
    merchant_df: pd.DataFrame,
    cb_df: pd.DataFrame,
) -> dict[str, Any]:
    """Run the full audit across all four datasets.

    Returns a structured dict containing all profile and issue data,
    ready to be passed to the report generator.
    """
    logger.info("Starting full data audit")

    report = {
        "transactions": {
            "profile": profile_dataset(txn_df, "transactions"),
            "issues": audit_transactions(txn_df),
        },
        "kyc": {
            "profile": profile_dataset(kyc_df, "kyc"),
            "issues": audit_kyc(kyc_df),
        },
        "merchants": {
            "profile": profile_dataset(merchant_df, "merchants"),
            "issues": audit_merchants(merchant_df),
        },
        "chargebacks": {
            "profile": profile_dataset(cb_df, "chargebacks"),
            "issues": audit_chargebacks(cb_df),
        },
        "referential_integrity": audit_referential_integrity(
            txn_df, kyc_df, merchant_df, cb_df
        ),
    }

    logger.info("Full data audit complete")
    return report
