"""
Pipeline Orchestrator for Milestone 2.
"""
from __future__ import annotations
import logging
import sys
import json
from pathlib import Path
import pandas as pd

from src.ingestion.loaders import load_all
from src.cleaning.transactions import clean_transactions
from src.cleaning.kyc import clean_kyc
from src.cleaning.merchants import clean_merchants
from src.cleaning.chargebacks import clean_chargebacks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("finguard.cleaning")

HERE = Path(__file__).resolve().parent.parent.parent
RAW_DIR = HERE / "data" / "raw"
PROCESSED_DIR = HERE / "data" / "processed"
QUARANTINE_DIR = HERE / "data" / "quarantine"
REPORTS_DIR = HERE / "reports"

def compute_fk_integrity(txn_df, kyc_df, merchant_df, cb_df) -> dict:
    """Compute referential integrity flags after normalization."""
    kyc_ids = set(kyc_df["user_id_normalized"].dropna())
    merchant_ids = set(merchant_df["merchant_id_normalized"].dropna())
    txn_ids = set(txn_df["txn_id_normalized"].dropna())
    
    integrity_stats = {}
    
    if "user_id_normalized" in txn_df.columns:
        txn_df["user_fk_missing"] = (~txn_df["user_id_normalized"].isin(kyc_ids)) & (txn_df["user_id_normalized"] != "")
        integrity_stats["txn_user_fk_missing"] = int(txn_df["user_fk_missing"].sum())
        
    if "merchant_id_normalized" in txn_df.columns:
        txn_df["merchant_fk_missing"] = (~txn_df["merchant_id_normalized"].isin(merchant_ids)) & (txn_df["merchant_id_normalized"] != "")
        integrity_stats["txn_merchant_fk_missing"] = int(txn_df["merchant_fk_missing"].sum())
        
    if "txn_id_normalized" in cb_df.columns:
        cb_df["chargeback_txn_fk_missing"] = (~cb_df["txn_id_normalized"].isin(txn_ids)) & (cb_df["txn_id_normalized"] != "")
        integrity_stats["cb_txn_fk_missing"] = int(cb_df["chargeback_txn_fk_missing"].sum())
        
    if "user_id_normalized" in cb_df.columns:
        cb_df["chargeback_user_fk_missing"] = (~cb_df["user_id_normalized"].isin(kyc_ids)) & (cb_df["user_id_normalized"] != "")
        integrity_stats["cb_user_fk_missing"] = int(cb_df["chargeback_user_fk_missing"].sum())
        
    if "merchant_id_normalized" in cb_df.columns:
        cb_df["chargeback_merchant_fk_missing"] = (~cb_df["merchant_id_normalized"].isin(merchant_ids)) & (cb_df["merchant_id_normalized"] != "")
        integrity_stats["cb_merchant_fk_missing"] = int(cb_df["chargeback_merchant_fk_missing"].sum())
        
    return integrity_stats

def generate_report(stats: dict, integrity_stats: dict):
    report_dict = {
        "datasets": stats,
        "referential_integrity": integrity_stats
    }
    
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "cleaning_report.json"
    md_path = REPORTS_DIR / "cleaning_report.md"
    
    with open(json_path, "w") as f:
        json.dump(report_dict, f, indent=2)
        
    lines = [
        "# FinGuard Data Cleaning & Normalization Report",
        "",
        "## Overview",
        "This report summarizes the cleaning and normalization applied to the raw datasets.",
        "",
        "## Dataset Statistics",
        "| Dataset | Raw Rows | Processed Rows | Exact Duplicates Removed |",
        "| --- | --- | --- | --- |"
    ]
    
    for name, s in stats.items():
        lines.append(f"| {name} | {s.get('raw_rows', 0)} | {s.get('processed_rows', 0)} | {s.get('exact_duplicates_removed', 0)} |")
        
    lines.extend([
        "",
        "## Referential Integrity (After Normalization)",
        "| Missing FK | Count |",
        "| --- | --- |"
    ])
    
    for k, v in integrity_stats.items():
        lines.append(f"| {k} | {v} |")
        
    with open(md_path, "w") as f:
        f.write("\n".join(lines))
        
    logger.info("Generated reports in %s", REPORTS_DIR)

def main():
    logger.info("Starting Data Cleaning Pipeline...")
    datasets = load_all(RAW_DIR)
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    
    stats = {}
    
    logger.info("Cleaning Transactions...")
    txn_clean, txn_stats = clean_transactions(datasets["transactions"])
    stats["transactions"] = txn_stats
    
    logger.info("Cleaning KYC...")
    kyc_clean, kyc_stats = clean_kyc(datasets["kyc"])
    stats["kyc"] = kyc_stats
    
    logger.info("Cleaning Merchants...")
    merch_clean, merch_stats = clean_merchants(datasets["merchants"])
    stats["merchants"] = merch_stats
    
    logger.info("Cleaning Chargebacks...")
    cb_clean, cb_stats = clean_chargebacks(datasets["chargebacks"])
    stats["chargebacks"] = cb_stats
    
    logger.info("Computing Referential Integrity...")
    integrity_stats = compute_fk_integrity(txn_clean, kyc_clean, merch_clean, cb_clean)
    
    logger.info("Saving Processed Datasets...")
    txn_clean.to_csv(PROCESSED_DIR / "transactions_clean.csv", index=False)
    kyc_clean.to_csv(PROCESSED_DIR / "kyc_clean.csv", index=False)
    merch_clean.to_csv(PROCESSED_DIR / "merchants_clean.csv", index=False)
    cb_clean.to_csv(PROCESSED_DIR / "chargebacks_clean.csv", index=False)
    
    generate_report(stats, integrity_stats)
    logger.info("Pipeline Complete!")

if __name__ == "__main__":
    main()
