"""
src/ingestion/loaders.py
------------------------
Robust data loaders for all four FinGuard raw datasets.

Rules:
- Raw files are NEVER modified.
- Records are NEVER silently dropped.
- Every column is initially read as a string (dtype=str) to preserve
  original representations for the audit phase.
- Useful errors are raised when files are missing or structurally corrupt.
- Each loader returns a pandas DataFrame (or list of dicts for JSON).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_raw_path(filename: str, raw_dir: Path) -> Path:
    """Return the absolute path to a raw file, raising FileNotFoundError
    with a helpful message if the file does not exist."""
    path = raw_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Raw file not found: {path}\n"
            f"Expected location: {raw_dir}\n"
            "Ensure raw files are placed in data/raw/ before running the audit."
        )
    return path


# ---------------------------------------------------------------------------
# CSV Loaders
# ---------------------------------------------------------------------------

def load_transactions(raw_dir: Path) -> pd.DataFrame:
    """Load UPI transaction CSV.

    All columns are read as strings to preserve original messy values
    (amount symbols, malformed timestamps, etc.) for the audit phase.

    Parameters
    ----------
    raw_dir : Path
        Directory containing the raw CSV files.

    Returns
    -------
    pd.DataFrame
        DataFrame with all original columns preserved as strings.

    Raises
    ------
    FileNotFoundError
        If the source file does not exist.
    ValueError
        If the file is empty or cannot be parsed as CSV.
    """
    path = _resolve_raw_path("track1_upi_transactions.csv", raw_dir)
    logger.info("Loading transactions from %s", path)

    try:
        df = pd.read_csv(
            path,
            dtype=str,          # preserve every value as-is
            keep_default_na=False,  # do NOT silently convert "" to NaN
            low_memory=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Transaction file is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Transaction file could not be parsed: {path}\n{exc}") from exc

    if df.empty:
        logger.warning("Transactions file loaded but contains no rows: %s", path)

    logger.info(
        "Transactions loaded: %d rows × %d columns", len(df), len(df.columns)
    )
    return df


def load_kyc(raw_dir: Path) -> pd.DataFrame:
    """Load KYC records CSV.

    Parameters
    ----------
    raw_dir : Path
        Directory containing the raw CSV files.

    Returns
    -------
    pd.DataFrame
        DataFrame with all original columns preserved as strings.
    """
    path = _resolve_raw_path("track1_kyc_records.csv", raw_dir)
    logger.info("Loading KYC records from %s", path)

    try:
        df = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            low_memory=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"KYC file is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"KYC file could not be parsed: {path}\n{exc}") from exc

    if df.empty:
        logger.warning("KYC file loaded but contains no rows: %s", path)

    logger.info("KYC records loaded: %d rows × %d columns", len(df), len(df.columns))
    return df


def load_merchants(raw_dir: Path) -> pd.DataFrame:
    """Load merchant master CSV.

    Parameters
    ----------
    raw_dir : Path
        Directory containing the raw CSV files.

    Returns
    -------
    pd.DataFrame
        DataFrame with all original columns preserved as strings.
    """
    path = _resolve_raw_path("track1_merchants_master.csv", raw_dir)
    logger.info("Loading merchants from %s", path)

    try:
        df = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            low_memory=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Merchants file is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Merchants file could not be parsed: {path}\n{exc}") from exc

    if df.empty:
        logger.warning("Merchants file loaded but contains no rows: %s", path)

    logger.info(
        "Merchants loaded: %d rows × %d columns", len(df), len(df.columns)
    )
    return df


# ---------------------------------------------------------------------------
# JSON Loader
# ---------------------------------------------------------------------------

def load_chargebacks(raw_dir: Path) -> pd.DataFrame:
    """Load chargeback complaints from JSON.

    The JSON file is expected to contain a list of complaint objects at
    the top level. If it contains a dict with a single list value, that
    list is extracted automatically.

    All field values are coerced to strings after loading to maintain
    audit-phase consistency with the CSV loaders.

    Parameters
    ----------
    raw_dir : Path
        Directory containing the raw JSON file.

    Returns
    -------
    pd.DataFrame
        DataFrame with all original fields preserved as strings.

    Raises
    ------
    FileNotFoundError
        If the source file does not exist.
    ValueError
        If the file cannot be parsed as JSON or has an unexpected structure.
    """
    path = _resolve_raw_path("track1_chargebacks.json", raw_dir)
    logger.info("Loading chargebacks from %s", path)

    try:
        with path.open("r", encoding="utf-8") as fh:
            raw: Any = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Chargeback file is not valid JSON: {path}\n{exc}"
        ) from exc

    # Handle list or single-key dict wrapping
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict):
        values = [v for v in raw.values() if isinstance(v, list)]
        if len(values) == 1:
            records = values[0]
        else:
            raise ValueError(
                f"Chargeback JSON is a dict but could not identify a single "
                f"list of records. Keys found: {list(raw.keys())}"
            )
    else:
        raise ValueError(
            f"Chargeback JSON has unexpected top-level type: {type(raw).__name__}. "
            "Expected list or dict."
        )

    if not records:
        logger.warning("Chargeback file loaded but contains no records: %s", path)

    df = pd.DataFrame(records)

    # Coerce all columns to string to match audit-phase convention,
    # but preserve the original NaN-free representation.
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: "" if (v is None) else str(v) if not isinstance(v, str) else v
        )

    logger.info(
        "Chargebacks loaded: %d rows × %d columns", len(df), len(df.columns)
    )
    return df


# ---------------------------------------------------------------------------
# Convenience loader — all datasets at once
# ---------------------------------------------------------------------------

def load_all(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all four raw datasets and return them in a named dict.

    Parameters
    ----------
    raw_dir : Path
        Directory containing the raw source files.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys: 'transactions', 'kyc', 'merchants', 'chargebacks'.
    """
    return {
        "transactions": load_transactions(raw_dir),
        "kyc": load_kyc(raw_dir),
        "merchants": load_merchants(raw_dir),
        "chargebacks": load_chargebacks(raw_dir),
    }
