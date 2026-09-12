"""
FinGuard — Milestone 1 audit runner.

Usage:
    python -m src.quality.audit          (from FinGuard/ directory)
    python run_audit.py                  (from FinGuard/ directory)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Configure logging before any imports that log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("finguard.runner")

# Resolve paths relative to this file's location
HERE      = Path(__file__).resolve().parent       # FinGuard/
RAW_DIR   = HERE / "data" / "raw"
REPORTS   = HERE / "reports"

# The raw files live one directory up (in DATATHON root)
_DATATHON_ROOT = HERE.parent
_RAW_FALLBACK  = _DATATHON_ROOT


def _locate_raw_dir() -> Path:
    """Find raw files — either in data/raw/ or the DATATHON root."""
    expected = ["track1_upi_transactions.csv",
                "track1_kyc_records.csv",
                "track1_merchants_master.csv",
                "track1_chargebacks.json"]

    for candidate in [RAW_DIR, _RAW_FALLBACK]:
        if all((candidate / f).exists() for f in expected):
            logger.info("Raw files found in: %s", candidate)
            return candidate

    logger.error(
        "Raw files not found in %s or %s", RAW_DIR, _RAW_FALLBACK
    )
    sys.exit(1)


def main() -> None:
    from src.ingestion.loaders import load_all
    from src.quality.audit import run_full_audit
    from src.quality.report import generate_reports

    raw_dir = _locate_raw_dir()

    logger.info("=== FinGuard Milestone 1 — Data Audit Starting ===")

    # --- Ingest ---
    logger.info("Loading datasets…")
    datasets = load_all(raw_dir)
    txn_df   = datasets["transactions"]
    kyc_df   = datasets["kyc"]
    merch_df = datasets["merchants"]
    cb_df    = datasets["chargebacks"]

    logger.info(
        "Loaded | txn=%d kyc=%d merchants=%d chargebacks=%d",
        len(txn_df), len(kyc_df), len(merch_df), len(cb_df),
    )

    # --- Audit ---
    audit_result = run_full_audit(txn_df, kyc_df, merch_df, cb_df)

    # --- Report ---
    json_path, md_path = generate_reports(audit_result, REPORTS)

    logger.info("=== Audit complete ===")
    logger.info("JSON report : %s", json_path)
    logger.info("MD report   : %s", md_path)

    # --- Console summary ---
    issues = audit_result.get("extracted_issues", {})
    all_issues = [i for section in issues.values() for i in section]
    non_low = [i for i in all_issues if i["severity"] != "LOW" and i["count"] > 0]
    critical = [i for i in all_issues if i["severity"] == "CRITICAL" and i["count"] > 0]

    print("\n" + "=" * 60)
    print("  FinGuard — Milestone 1 Audit Summary")
    print("=" * 60)
    print(f"  Transactions : {len(txn_df):,} rows")
    print(f"  KYC records  : {len(kyc_df):,} rows")
    print(f"  Merchants    : {len(merch_df):,} rows")
    print(f"  Chargebacks  : {len(cb_df):,} rows")
    print(f"\n  Issues found (non-LOW): {len(non_low)}")
    print(f"  CRITICAL: {sum(1 for i in all_issues if i['severity']=='CRITICAL' and i['count']>0)}")
    print(f"  HIGH    : {sum(1 for i in all_issues if i['severity']=='HIGH' and i['count']>0)}")
    print(f"  MEDIUM  : {sum(1 for i in all_issues if i['severity']=='MEDIUM' and i['count']>0)}")
    if critical:
        print("\n  ⚠ CRITICAL issues:")
        for i in critical:
            print(f"    - {i['issue_name']}: {i['count']}")
    print("=" * 60)
    print(f"\n  Reports:\n  {json_path}\n  {md_path}\n")


if __name__ == "__main__":
    main()
