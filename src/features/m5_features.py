#!/usr/bin/env python3
"""
FinGuard M5 — Risk Feature Engineering

This script generates risk features strictly following M5 boundaries.
It creates features at four levels: Transaction, User, Merchant, and Chargeback.
All features are explicitly classified to prevent temporal leakage.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("m5_features")

# Paths
HERE = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = HERE / "data" / "processed"
FEATURES_DIR = PROCESSED_DIR / "features"
REPORTS_DIR = HERE / "reports"

FEATURES_DIR.mkdir(parents=True, exist_ok=True)

MIN_N_OBSERVATIONS = 5

def load_datasets():
    logger.info("Loading integrated M3 datasets...")
    txn = pd.read_csv(PROCESSED_DIR / "finguard_transactions.csv", dtype=str)
    
    # Safely convert numerics for transaction
    num_cols = ["amount_numeric", "chargeback_count", "total_disputed_amount", "chargeback_report_delay_hours"]
    for c in num_cols:
        if c in txn.columns:
            txn[c] = pd.to_numeric(txn[c], errors="coerce")
            
    txn["timestamp_clean"] = pd.to_datetime(txn["timestamp_clean"], errors="coerce")
    
    # Boolean conversions
    bool_cols = ["amount_is_negative", "amount_missing", "utr_missing_flag", "transaction_has_kyc", 
                 "transaction_has_merchant", "has_chargeback", "dispute_after_7_days_flag",
                 "duplicate_txn_id_flag", "referential_integrity_issue_flag", "timestamp_invalid_flag"]
    for c in bool_cols:
        if c in txn.columns:
            txn[c] = txn[c].map({"True": True, "False": False, True: True, False: False}).astype(bool)

    if "chargeback_report_delay_hours" in txn.columns:
        txn["invalid_chargeback_delay_flag"] = (txn["has_chargeback"] == True) & (txn["chargeback_report_delay_hours"] < 0)

    if "utr_missing_flag" not in txn.columns:
        txn["utr_missing_flag"] = txn["utr_missing"].fillna("False").map({"True": True, "False": False}).astype(bool)

    usr = pd.read_csv(PROCESSED_DIR / "users_analytics.csv", dtype=str)
    mrc = pd.read_csv(PROCESSED_DIR / "merchants_analytics.csv", dtype=str)
    cb = pd.read_csv(PROCESSED_DIR / "chargebacks_aggregated.csv", dtype=str)

    return txn, usr, mrc, cb

def build_transaction_features(txn: pd.DataFrame, usr: pd.DataFrame, mrc: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building transaction features...")
    features = pd.DataFrame()
    
    features["txn_id_normalized"] = txn["txn_id_normalized"]
    features["user_id_normalized"] = txn["user_id_normalized"]
    features["merchant_id_normalized"] = txn["merchant_id_normalized"]

    features["amount_numeric"] = txn["amount_numeric"]
    features["amount_abs"] = txn["amount_numeric"].abs()
    valid_amts = features["amount_numeric"].dropna()
    features["amount_percentile"] = features["amount_numeric"].rank(pct=True) * 100
    features["negative_amount_flag"] = txn.get("amount_is_negative", False).fillna(False).astype(bool)
    features["amount_missing_flag"] = txn["amount_numeric"].isna()

    q1 = valid_amts.quantile(0.25)
    q3 = valid_amts.quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 3 * iqr
    features["amount_iqr_anomaly_flag"] = features["amount_numeric"] > upper_fence

    dt = txn["timestamp_clean"]
    features["transaction_date"] = dt.dt.date
    features["transaction_hour"] = dt.dt.hour
    features["transaction_day"] = dt.dt.day
    features["transaction_week"] = dt.dt.isocalendar().week
    features["transaction_month"] = dt.dt.month
    features["day_of_week"] = dt.dt.dayofweek
    features["weekend_flag"] = dt.dt.dayofweek >= 5

    features["success_flag"] = txn["status_clean"] == "SUCCESS"
    features["failed_flag"] = txn["status_clean"] == "FAILED"
    features["pending_flag"] = txn["status_clean"] == "PENDING"

    features["missing_utr_flag"] = txn.get("utr_missing_flag", False).fillna(False).astype(bool)
    features["kyc_match_flag"] = txn.get("transaction_has_kyc", False).fillna(False).astype(bool)
    features["merchant_match_flag"] = txn.get("transaction_has_merchant", False).fillna(False).astype(bool)
    features["referential_integrity_issue_flag"] = txn.get("referential_integrity_issue_flag", False).fillna(False).astype(bool)
    features["timestamp_invalid_flag"] = txn.get("timestamp_invalid_flag", False).fillna(False).astype(bool)
    features["duplicate_txn_id_flag"] = txn.get("duplicate_txn_id_flag", False).fillna(False).astype(bool)

    features["has_chargeback"] = txn.get("has_chargeback", False).fillna(False).astype(bool)
    features["chargeback_count"] = txn.get("chargeback_count", 0).fillna(0)
    features["total_disputed_amount"] = txn.get("total_disputed_amount", 0.0).fillna(0.0)
    features["max_dispute_severity"] = txn.get("max_severity", "")
    features["dispute_after_7_days_flag"] = txn.get("dispute_after_7_days_flag", False).fillna(False).astype(bool)
    features["chargeback_report_delay_hours"] = txn.get("chargeback_report_delay_hours", pd.NA)
    features["invalid_chargeback_delay_flag"] = txn.get("invalid_chargeback_delay_flag", False).fillna(False).astype(bool)

    usr_map = usr.set_index("user_id_normalized")
    features["user_transaction_count"] = txn["user_id_normalized"].map(usr_map["transaction_count"].astype(float)).fillna(0)
    features["user_total_transaction_amount"] = txn["user_id_normalized"].map(usr_map["total_transaction_amount"].astype(float)).fillna(0.0)
    features["user_avg_transaction_amount"] = txn["user_id_normalized"].map(usr_map["avg_transaction_amount"].astype(float)).fillna(0.0)
    
    mrc_map = mrc.set_index("merchant_id_normalized")
    features["merchant_transaction_count"] = txn["merchant_id_normalized"].map(mrc_map["transaction_count"].astype(float)).fillna(0)
    features["merchant_total_transaction_amount"] = txn["merchant_id_normalized"].map(mrc_map["total_transaction_amount"].astype(float)).fillna(0.0)
    features["merchant_avg_transaction_amount"] = txn["merchant_id_normalized"].map(mrc_map["avg_transaction_amount"].astype(float)).fillna(0.0)

    user_stats = txn.groupby("user_id_normalized")["amount_numeric"].agg(["mean", "std", "count"])
    features["user_amount_mean"] = txn["user_id_normalized"].map(user_stats["mean"])
    features["user_amount_std"] = txn["user_id_normalized"].map(user_stats["std"])
    features["user_amount_zscore"] = np.where(
        txn["user_id_normalized"].map(user_stats["count"]) >= MIN_N_OBSERVATIONS,
        (features["amount_numeric"] - features["user_amount_mean"]) / features["user_amount_std"].replace(0, np.nan),
        pd.NA
    )
    features["user_relative_amount_anomaly"] = features["user_amount_zscore"].apply(lambda z: abs(z) > 3 if pd.notna(z) else False)

    mrc_stats = txn.groupby("merchant_id_normalized")["amount_numeric"].agg(["mean", "std", "count"])
    features["merchant_amount_mean"] = txn["merchant_id_normalized"].map(mrc_stats["mean"])
    features["merchant_amount_std"] = txn["merchant_id_normalized"].map(mrc_stats["std"])
    features["merchant_amount_zscore"] = np.where(
        txn["merchant_id_normalized"].map(mrc_stats["count"]) >= MIN_N_OBSERVATIONS,
        (features["amount_numeric"] - features["merchant_amount_mean"]) / features["merchant_amount_std"].replace(0, np.nan),
        pd.NA
    )
    features["merchant_relative_amount_anomaly"] = features["merchant_amount_zscore"].apply(lambda z: abs(z) > 3 if pd.notna(z) else False)

    return features

def build_user_features(txn: pd.DataFrame, usr: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building user features...")
    user_grp = txn.groupby("user_id_normalized")
    
    features = pd.DataFrame(index=user_grp.indices.keys())
    features.index.name = "user_id_normalized"
    
    features["transaction_count"] = user_grp.size()
    features["total_transaction_amount"] = user_grp["amount_numeric"].sum(min_count=1)
    features["avg_transaction_amount"] = user_grp["amount_numeric"].mean()
    features["median_transaction_amount"] = user_grp["amount_numeric"].median()
    features["amount_std"] = user_grp["amount_numeric"].std()
    
    features["successful_transaction_count"] = user_grp.apply(lambda g: (g["status_clean"] == "SUCCESS").sum())
    features["failed_transaction_count"] = user_grp.apply(lambda g: (g["status_clean"] == "FAILED").sum())
    features["pending_transaction_count"] = user_grp.apply(lambda g: (g["status_clean"] == "PENDING").sum())
    
    features["success_rate"] = features["successful_transaction_count"] / features["transaction_count"]
    features["failure_rate"] = features["failed_transaction_count"] / features["transaction_count"]
    features["pending_rate"] = features["pending_transaction_count"] / features["transaction_count"]
    
    features["chargeback_transaction_count"] = user_grp.apply(lambda g: g["has_chargeback"].fillna(False).sum())
    features["chargeback_rate"] = features["chargeback_transaction_count"] / features["transaction_count"]
    features["total_disputed_amount"] = user_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].sum())
    features["avg_disputed_amount"] = user_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].mean())
    features["median_disputed_amount"] = user_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].median())
    features["max_disputed_amount"] = user_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].max())
    
    features["dispute_after_7_days_count"] = user_grp.apply(lambda g: g["dispute_after_7_days_flag"].fillna(False).sum())
    features["dispute_after_7_days_rate"] = np.where(features["chargeback_transaction_count"] > 0, features["dispute_after_7_days_count"] / features["chargeback_transaction_count"], 0)
    
    features["unique_merchant_count"] = user_grp["merchant_id_normalized"].nunique()
    features["unique_category_count"] = user_grp["merchant_category_clean"].nunique()
    features["negative_transaction_count"] = user_grp.apply(lambda g: g["amount_is_negative"].fillna(False).sum())
    features["missing_utr_count"] = user_grp.apply(lambda g: g["utr_missing_flag"].fillna(False).sum())
    
    usr_map = usr.set_index("user_id_normalized")
    features["kyc_status"] = features.index.map(usr_map["kyc_status_clean"]).fillna("UNKNOWN")
    features["kyc_match_flag"] = features.index.map(usr_map["kyc_match_flag"].map({"True": True, "False": False})).fillna(False)
    features["kyc_duplicate_entity_flag"] = features.index.map(usr_map["kyc_duplicate_entity_flag"].map({"True": True, "False": False})).fillna(False)

    return features.reset_index()

def build_merchant_features(txn: pd.DataFrame, mrc: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building merchant features...")
    mrc_grp = txn.groupby("merchant_id_normalized")
    
    features = pd.DataFrame(index=mrc_grp.indices.keys())
    features.index.name = "merchant_id_normalized"
    
    features["transaction_count"] = mrc_grp.size()
    features["total_transaction_amount"] = mrc_grp["amount_numeric"].sum(min_count=1)
    features["avg_transaction_amount"] = mrc_grp["amount_numeric"].mean()
    features["median_transaction_amount"] = mrc_grp["amount_numeric"].median()
    features["amount_std"] = mrc_grp["amount_numeric"].std()
    
    features["successful_transaction_count"] = mrc_grp.apply(lambda g: (g["status_clean"] == "SUCCESS").sum())
    features["failed_transaction_count"] = mrc_grp.apply(lambda g: (g["status_clean"] == "FAILED").sum())
    features["pending_transaction_count"] = mrc_grp.apply(lambda g: (g["status_clean"] == "PENDING").sum())
    
    features["success_rate"] = features["successful_transaction_count"] / features["transaction_count"]
    features["failure_rate"] = features["failed_transaction_count"] / features["transaction_count"]
    features["pending_rate"] = features["pending_transaction_count"] / features["transaction_count"]
    
    features["chargeback_transaction_count"] = mrc_grp.apply(lambda g: g["has_chargeback"].fillna(False).sum())
    features["chargeback_rate"] = features["chargeback_transaction_count"] / features["transaction_count"]
    features["total_disputed_amount"] = mrc_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].sum())
    features["disputed_amount_ratio"] = np.where(features["total_transaction_amount"] > 0, features["total_disputed_amount"] / features["total_transaction_amount"], 0)
    features["avg_disputed_amount"] = mrc_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].mean())
    features["median_disputed_amount"] = mrc_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].median())
    features["max_disputed_amount"] = mrc_grp.apply(lambda g: g.loc[g["has_chargeback"] == True, "total_disputed_amount"].max())
    
    features["dispute_after_7_days_count"] = mrc_grp.apply(lambda g: g["dispute_after_7_days_flag"].fillna(False).sum())
    features["dispute_after_7_days_rate"] = np.where(features["chargeback_transaction_count"] > 0, features["dispute_after_7_days_count"] / features["chargeback_transaction_count"], 0)
    
    features["unique_user_count"] = mrc_grp["user_id_normalized"].nunique()
    features["unique_category_count"] = mrc_grp["merchant_category_clean"].nunique()
    features["negative_transaction_count"] = mrc_grp.apply(lambda g: g["amount_is_negative"].fillna(False).sum())
    features["missing_utr_count"] = mrc_grp.apply(lambda g: g["utr_missing_flag"].fillna(False).sum())
    
    mrc_map = mrc.set_index("merchant_id_normalized")
    features["merchant_status"] = features.index.map(mrc_map["merchant_status_clean"]).fillna("UNKNOWN")
    features["merchant_category"] = features.index.map(mrc_map["merchant_category_clean"]).fillna("UNKNOWN")
    features["mcc"] = features.index.map(mrc_map["mcc_clean"]).fillna("UNKNOWN")
    features["merchant_duplicate_entity_flag"] = features.index.map(mrc_map["merchant_duplicate_entity_flag"].map({"True": True, "False": False})).fillna(False)

    return features.reset_index()

def build_chargeback_features(cb: pd.DataFrame, txn: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building chargeback features...")
    features = pd.DataFrame()
    features["txn_id_normalized"] = cb["txn_id_normalized"]
    features["total_disputed_amount"] = pd.to_numeric(cb["total_disputed_amount"], errors="coerce")
    features["chargeback_count"] = pd.to_numeric(cb["chargeback_count"], errors="coerce")
    features["max_severity"] = cb["max_severity"]
    
    txn_delays = txn[["txn_id_normalized", "chargeback_report_delay_hours", "dispute_after_7_days_flag", "invalid_chargeback_delay_flag"]]
    features = features.merge(txn_delays, on="txn_id_normalized", how="left")
    
    features["invalid_chargeback_delay_flag"] = features["invalid_chargeback_delay_flag"].fillna(False).astype(bool)
    features["dispute_after_7_days_flag"] = features["dispute_after_7_days_flag"].fillna(False).astype(bool)

    return features

def main():
    txn, usr, mrc, cb = load_datasets()
    
    txn_features = build_transaction_features(txn, usr, mrc)
    usr_features = build_user_features(txn, usr)
    mrc_features = build_merchant_features(txn, mrc)
    cb_features = build_chargeback_features(cb, txn)
    
    logger.info(f"Transaction Features Shape: {txn_features.shape}")
    logger.info(f"User Features Shape: {usr_features.shape}")
    logger.info(f"Merchant Features Shape: {mrc_features.shape}")
    logger.info(f"Chargeback Features Shape: {cb_features.shape}")
    
    txn_features.to_csv(FEATURES_DIR / "transaction_risk_features.csv", index=False)
    usr_features.to_csv(FEATURES_DIR / "user_risk_features.csv", index=False)
    mrc_features.to_csv(FEATURES_DIR / "merchant_risk_features.csv", index=False)
    cb_features.to_csv(FEATURES_DIR / "chargeback_risk_features.csv", index=False)
    
    logger.info("M5 Feature Engineering completed.")

if __name__ == "__main__":
    main()
