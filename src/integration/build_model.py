"""
Unified Analytics Data Model Builder.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_model")

HERE = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = HERE / "data" / "processed"
REPORTS_DIR = HERE / "reports"

def load_processed() -> dict[str, pd.DataFrame]:
    """Load cleaned data, ensuring IDs are parsed as strings."""
    return {
        "transactions": pd.read_csv(PROCESSED_DIR / "transactions_clean.csv", dtype=str),
        "kyc": pd.read_csv(PROCESSED_DIR / "kyc_clean.csv", dtype=str),
        "merchants": pd.read_csv(PROCESSED_DIR / "merchants_clean.csv", dtype=str),
        "chargebacks": pd.read_csv(PROCESSED_DIR / "chargebacks_clean.csv", dtype=str)
    }

def convert_types(df: pd.DataFrame, num_cols: list[str], time_cols: list[str]):
    """Convert specified columns to numeric/datetime."""
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in time_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def resolve_entities(df: pd.DataFrame, entity_id_col: str, sort_cols: list[str], ascending: list[bool]) -> tuple[pd.DataFrame, int]:
    """Resolve duplicate entities by sorting on completeness/recency and taking the first."""
    # Count non-nulls for completeness
    df["_completeness"] = df.notna().sum(axis=1)
    
    # Sort
    df_sorted = df.sort_values(by=["_completeness"] + sort_cols, ascending=[False] + ascending)
    
    # Find duplicates
    dup_counts = df_sorted.groupby(entity_id_col).size()
    dup_entities = set(dup_counts[dup_counts > 1].index)
    
    # Deduplicate
    df_canonical = df_sorted.drop_duplicates(subset=[entity_id_col], keep="first").copy()
    df_canonical.drop(columns=["_completeness"], inplace=True)
    
    return df_canonical, len(dup_entities)

def aggregate_chargebacks(cb_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate chargebacks to the transaction level."""
    # Ensure types
    cb_df = convert_types(cb_df, ["disputed_amount_numeric"], ["transaction_timestamp_clean", "reported_timestamp_clean", "bank_response_timestamp_clean"])
    
    agg = cb_df.groupby("txn_id_normalized").agg(
        chargeback_count=("complaint_id_normalized", "count"),
        total_disputed_amount=("disputed_amount_numeric", "sum"),
        max_severity=("severity_clean", lambda x: ",".join(sorted(set(x.dropna())))),
        first_chargeback_timestamp=("reported_timestamp_clean", "min"),
        latest_chargeback_timestamp=("reported_timestamp_clean", "max")
    ).reset_index()
    
    return agg

def build_unified_model():
    logger.info("Loading cleaned datasets...")
    datasets = load_processed()
    
    txn = datasets["transactions"]
    kyc = datasets["kyc"]
    merch = datasets["merchants"]
    cb = datasets["chargebacks"]
    
    txn = convert_types(txn, ["amount_numeric"], ["timestamp_clean"])
    kyc = convert_types(kyc, ["monthly_income_numeric"], ["signup_timestamp_clean", "date_of_birth_clean"])
    merch = convert_types(merch, ["declared_avg_ticket_size_numeric"], ["onboarding_date_clean"])
    cb = convert_types(cb, ["disputed_amount_numeric"], ["reported_timestamp_clean"])
    
    stats = {}
    stats["initial_transactions"] = len(txn)
    
    # 1. Resolve KYC
    logger.info("Resolving KYC duplicates...")
    kyc_canonical, kyc_dup_count = resolve_entities(kyc, "user_id_normalized", ["signup_timestamp_clean"], [False])
    kyc_canonical["kyc_duplicate_entity_flag"] = kyc_canonical["user_id_normalized"].isin(
        kyc.groupby("user_id_normalized").filter(lambda x: len(x) > 1)["user_id_normalized"]
    )
    stats["kyc_duplicate_entities_resolved"] = kyc_dup_count
    stats["kyc_canonical_rows"] = len(kyc_canonical)
    
    # 2. Resolve Merchants
    logger.info("Resolving Merchant duplicates...")
    merch_canonical, merch_dup_count = resolve_entities(merch, "merchant_id_normalized", ["onboarding_date_clean"], [False])
    merch_canonical["merchant_duplicate_entity_flag"] = merch_canonical["merchant_id_normalized"].isin(
        merch.groupby("merchant_id_normalized").filter(lambda x: len(x) > 1)["merchant_id_normalized"]
    )
    stats["merchant_duplicate_entities_resolved"] = merch_dup_count
    stats["merchant_canonical_rows"] = len(merch_canonical)
    
    # 3. Aggregate Chargebacks
    logger.info("Aggregating Chargebacks...")
    cb_agg = aggregate_chargebacks(cb)
    cb_agg.to_csv(PROCESSED_DIR / "chargebacks_aggregated.csv", index=False)
    stats["aggregated_chargeback_rows"] = len(cb_agg)
    
    # 4. Integrate Transactions
    logger.info("Integrating Transactions...")
    
    # Select columns to join from KYC
    kyc_cols = ["user_id_normalized", "kyc_status_clean", "pan_clean", "aadhaar_clean", 
                "monthly_income_numeric", "city_clean", "state_clean", "occupation_clean", 
                "kyc_duplicate_entity_flag"]
    
    # Select columns to join from Merchants
    merch_cols = ["merchant_id_normalized", "mcc_clean", "merchant_category_clean", 
                  "merchant_status_clean", "business_type_clean", "merchant_duplicate_entity_flag"]
    
    # Join KYC
    df = pd.merge(txn, kyc_canonical[kyc_cols], on="user_id_normalized", how="left")
    
    # Join Merchants (Rename mcc_clean from merchant if it conflicts)
    merch_canonical_sub = merch_canonical[merch_cols].rename(columns={"mcc_clean": "merchant_mcc_clean"})
    df = pd.merge(df, merch_canonical_sub, on="merchant_id_normalized", how="left")
    
    # Join Chargebacks
    df = pd.merge(df, cb_agg, on="txn_id_normalized", how="left")
    
    # Assert row count
    if len(df) != len(txn):
        logger.error(f"Join explosion! Initial: {len(txn)}, Final: {len(df)}")
        raise ValueError("Many-to-many join explosion occurred.")
        
    stats["integrated_transactions"] = len(df)
    
    # 5. Feature Engineering
    logger.info("Engineering features...")
    df["transaction_has_kyc"] = df["kyc_status_clean"].notna()
    df["transaction_has_merchant"] = df["merchant_status_clean"].notna()
    df["transaction_has_chargeback"] = df["chargeback_count"].notna() & (df["chargeback_count"] > 0)
    
    # Missing UTR
    df["utr_missing_flag"] = df["utr_clean"].isna() | (df["utr_clean"] == "")
    # Negative Amount
    df["amount_negative_flag"] = (df["amount_numeric"] < 0)
    # Invalid Timestamp (we have timestamp_parse_failed from milestone 2, but let's check timestamp_clean)
    df["timestamp_invalid_flag"] = df["timestamp_clean"].isna()
    # Duplicate TXN ID
    df["duplicate_txn_id_flag"] = df["txn_id_duplicate_count"].astype(float) > 1
    # Referential Integrity Issue
    df["referential_integrity_issue_flag"] = (~df["transaction_has_kyc"]) | (~df["transaction_has_merchant"])
    
    # Chargeback reporting delay
    def calc_delay(row):
        if pd.notna(row["timestamp_clean"]) and pd.notna(row["first_chargeback_timestamp"]):
            delay = (row["first_chargeback_timestamp"] - row["timestamp_clean"]).total_seconds() / 3600.0
            return delay if delay >= 0 else np.nan
        return np.nan
        
    df["chargeback_report_delay_hours"] = df.apply(calc_delay, axis=1)
    df["dispute_after_7_days_flag"] = df["chargeback_report_delay_hours"] > (7 * 24)
    
    df["has_chargeback"] = df["transaction_has_chargeback"]
    
    # Save
    df.to_csv(PROCESSED_DIR / "finguard_transactions.csv", index=False)
    
    # 6. Entity Analytics Tables
    logger.info("Building entity analytics tables...")
    
    # users_analytics
    users_agg = df.groupby("user_id_normalized").agg(
        transaction_count=("txn_id_normalized", "count"),
        total_transaction_amount=("amount_numeric", "sum"),
        successful_transaction_count=("status_clean", lambda x: (x == "SUCCESS").sum()),
        failed_transaction_count=("status_clean", lambda x: (x == "FAILED").sum()),
        chargeback_count=("chargeback_count", "sum"),
        total_disputed_amount=("total_disputed_amount", "sum")
    ).reset_index()
    
    users_agg["avg_transaction_amount"] = np.where(
        users_agg["transaction_count"] > 0, 
        users_agg["total_transaction_amount"] / users_agg["transaction_count"], 
        0
    )
    
    users_analytics = pd.merge(users_agg, kyc_canonical[["user_id_normalized", "kyc_status_clean", "kyc_duplicate_entity_flag"]], on="user_id_normalized", how="left")
    users_analytics["kyc_match_flag"] = users_analytics["kyc_status_clean"].notna()
    users_analytics.to_csv(PROCESSED_DIR / "users_analytics.csv", index=False)
    stats["users_analytics_rows"] = len(users_analytics)
    
    # merchants_analytics
    merch_agg = df.groupby("merchant_id_normalized").agg(
        transaction_count=("txn_id_normalized", "count"),
        total_transaction_amount=("amount_numeric", "sum"),
        successful_transaction_count=("status_clean", lambda x: (x == "SUCCESS").sum()),
        failed_transaction_count=("status_clean", lambda x: (x == "FAILED").sum()),
        chargeback_count=("chargeback_count", "sum"),
        total_disputed_amount=("total_disputed_amount", "sum")
    ).reset_index()
    
    merch_agg["avg_transaction_amount"] = np.where(
        merch_agg["transaction_count"] > 0, 
        merch_agg["total_transaction_amount"] / merch_agg["transaction_count"], 
        0
    )
    
    merch_agg["chargeback_rate"] = np.where(
        merch_agg["transaction_count"] > 0,
        merch_agg["chargeback_count"] / merch_agg["transaction_count"],
        0
    )
    
    merch_agg["disputed_amount_ratio"] = np.where(
        merch_agg["total_transaction_amount"] > 0,
        merch_agg["total_disputed_amount"] / merch_agg["total_transaction_amount"],
        0
    )
    
    merch_agg["success_rate"] = np.where(
        merch_agg["transaction_count"] > 0,
        merch_agg["successful_transaction_count"] / merch_agg["transaction_count"],
        0
    )
    
    merch_agg["failure_rate"] = np.where(
        merch_agg["transaction_count"] > 0,
        merch_agg["failed_transaction_count"] / merch_agg["transaction_count"],
        0
    )
    
    merch_analytics = pd.merge(merch_agg, merch_canonical[["merchant_id_normalized", "merchant_status_clean", "merchant_category_clean", "mcc_clean", "merchant_duplicate_entity_flag"]], on="merchant_id_normalized", how="left")
    merch_analytics.to_csv(PROCESSED_DIR / "merchants_analytics.csv", index=False)
    stats["merchants_analytics_rows"] = len(merch_analytics)
    
    # 7. Reporting
    logger.info("Generating reports...")
    
    stats["transaction_has_kyc_count"] = int(df["transaction_has_kyc"].sum())
    stats["transaction_has_merchant_count"] = int(df["transaction_has_merchant"].sum())
    stats["transaction_has_chargeback_count"] = int(df["transaction_has_chargeback"].sum())
    
    with open(REPORTS_DIR / "integration_report.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    md_lines = [
        "# FinGuard Milestone 3: Integration Report",
        "",
        "## Summary Statistics",
        f"- Initial Transaction Rows: {stats['initial_transactions']}",
        f"- Integrated Transaction Rows: {stats['integrated_transactions']}",
        f"- Users Analytics Rows: {stats['users_analytics_rows']}",
        f"- Merchants Analytics Rows: {stats['merchants_analytics_rows']}",
        f"- Aggregated Chargebacks Rows: {stats['aggregated_chargeback_rows']}",
        "",
        "## Entity Resolution",
        f"- KYC Collision Groups Resolved: {stats['kyc_duplicate_entities_resolved']} (Canonical records: {stats['kyc_canonical_rows']})",
        f"- Merchant Collision Groups Resolved: {stats['merchant_duplicate_entities_resolved']} (Canonical records: {stats['merchant_canonical_rows']})",
        "",
        "## Integration Quality",
        f"- Transactions matching KYC: {stats['transaction_has_kyc_count']} ({(stats['transaction_has_kyc_count']/stats['integrated_transactions'])*100:.2f}%)",
        f"- Transactions matching Merchants: {stats['transaction_has_merchant_count']} ({(stats['transaction_has_merchant_count']/stats['integrated_transactions'])*100:.2f}%)",
        f"- Transactions with Chargebacks: {stats['transaction_has_chargeback_count']}",
        "",
        "**PASS**: Join explosion prevented. Row counts strictly conserved."
    ]
    
    with open(REPORTS_DIR / "integration_report.md", "w") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    build_unified_model()
