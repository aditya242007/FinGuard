"""
M8 Dashboard Data Preparation Script
====================================
Reads authoritative M3-M7 outputs and produces slim, dashboard-ready JSON files
so the browser never has to parse or merge raw CSVs.

FROZEN: Does NOT modify any M0-M7 source files.
OUTPUT: dashboard/public/data/*.json (new files)
        dashboard/public/data/*.csv  (copied unchanged from M3-M7 outputs)
"""
import json
import os
import shutil
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

BASE_DIR = Path("data/processed")
DEST_DIR = Path("dashboard/public/data")
os.makedirs(DEST_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Load authoritative M3–M7 processed outputs
# ---------------------------------------------------------------------------
print("[1/7] Loading authoritative M3-M7 outputs...")

txn = pd.read_csv(BASE_DIR / "finguard_transactions.csv", low_memory=False)
txn_risk = pd.read_csv(BASE_DIR / "risk" / "transaction_risk_scores.csv", low_memory=False)
user_analytics = pd.read_csv(BASE_DIR / "users_analytics.csv", low_memory=False)
user_risk = pd.read_csv(BASE_DIR / "risk" / "user_risk_scores.csv", low_memory=False)
merchant_analytics = pd.read_csv(BASE_DIR / "merchants_analytics.csv", low_memory=False)
merchant_risk = pd.read_csv(BASE_DIR / "risk" / "merchant_risk_scores.csv", low_memory=False)
clusters = pd.read_csv(BASE_DIR / "graph" / "suspicious_clusters.csv", low_memory=False)
cluster_members = pd.read_csv(BASE_DIR / "graph" / "cluster_members.csv", low_memory=False)
chargebacks = pd.read_csv(BASE_DIR / "chargebacks_aggregated.csv", low_memory=False)

print(f"  transactions: {len(txn):,} rows")
print(f"  transaction_risk_scores: {len(txn_risk):,} rows")
print(f"  users_analytics: {len(user_analytics):,} rows")
print(f"  user_risk_scores: {len(user_risk):,} rows")
print(f"  merchants_analytics: {len(merchant_analytics):,} rows")
print(f"  merchant_risk_scores: {len(merchant_risk):,} rows")
print(f"  suspicious_clusters: {len(clusters):,} rows")
print(f"  cluster_members: {len(cluster_members):,} rows")
print(f"  chargebacks_aggregated: {len(chargebacks):,} rows")


# ---------------------------------------------------------------------------
# 2. Build slim transaction records (join with M6 risk scores)
# ---------------------------------------------------------------------------
print("\n[2/7] Merging M6 risk scores into transaction records...")

TXN_COLS = [
    "txn_id_normalized",
    "timestamp_clean",
    "amount_numeric",          # authoritative signed amount (NOT amount_abs)
    "status_clean",
    "merchant_category_clean",
    "kyc_status_clean",
    "has_chargeback",
    "chargeback_count",
    "total_disputed_amount",
    "dispute_after_7_days_flag",
    "user_id_normalized",
    "merchant_id_normalized",
    "utr_missing_flag",
    "amount_negative_flag",
    "transaction_has_kyc",
    "transaction_has_merchant",
]

txn_slim = txn[TXN_COLS].copy()

# Join M6 risk scores (transaction_time and retrospective)
RISK_COLS = [
    "txn_id",
    "transaction_time_risk_score",
    "transaction_time_risk_level",
    "retrospective_risk_score",
    "retrospective_risk_level",
    "explanation",
    "top_risk_signal_1",
    "top_risk_signal_2",
    "top_risk_signal_3",
]
txn_risk_slim = txn_risk[RISK_COLS].copy()
txn_risk_slim = txn_risk_slim.rename(columns={"txn_id": "txn_id_normalized"})

txn_merged = txn_slim.merge(txn_risk_slim, on="txn_id_normalized", how="left")
assert len(txn_merged) == 20_000, f"Expected 20000 rows, got {len(txn_merged)}"

# Validation checks
total_value = txn_merged["amount_numeric"].sum()
assert abs(total_value - 239_232_643.30) < 1.0, f"Total value mismatch: {total_value}"
print(f"  Merged transactions: {len(txn_merged):,}")
print(f"  Total value (authoritative): ₹{total_value:,.2f}")
print(f"  Average value: ₹{total_value/len(txn_merged):,.2f}")

# Write as JSON (much faster browser parse vs CSV for this slim set)
txn_merged["timestamp_clean"] = txn_merged["timestamp_clean"].fillna("")
txn_merged["explanation"] = txn_merged["explanation"].fillna("")
txn_merged["top_risk_signal_1"] = txn_merged["top_risk_signal_1"].fillna("")
txn_merged["top_risk_signal_2"] = txn_merged["top_risk_signal_2"].fillna("")
txn_merged["top_risk_signal_3"] = txn_merged["top_risk_signal_3"].fillna("")
txn_merged["kyc_status_clean"] = txn_merged["kyc_status_clean"].fillna("UNKNOWN")
txn_merged["merchant_category_clean"] = txn_merged["merchant_category_clean"].fillna("UNKNOWN")
txn_merged["transaction_time_risk_level"] = txn_merged["transaction_time_risk_level"].fillna("UNKNOWN")
txn_merged["retrospective_risk_level"] = txn_merged["retrospective_risk_level"].fillna("UNKNOWN")
txn_merged["has_chargeback"] = txn_merged["has_chargeback"].astype(bool)
txn_merged["amount_negative_flag"] = txn_merged["amount_negative_flag"].astype(bool)
txn_merged["utr_missing_flag"] = txn_merged["utr_missing_flag"].astype(bool)
txn_merged["dispute_after_7_days_flag"] = txn_merged["dispute_after_7_days_flag"].astype(bool)
txn_merged["transaction_has_kyc"] = txn_merged["transaction_has_kyc"].astype(bool)
txn_merged["transaction_has_merchant"] = txn_merged["transaction_has_merchant"].astype(bool)
# Fill numeric NaNs with 0 so JSON has no null values for numeric fields
txn_merged["chargeback_count"] = txn_merged["chargeback_count"].fillna(0).astype(int)
txn_merged["total_disputed_amount"] = txn_merged["total_disputed_amount"].fillna(0.0)
txn_merged["transaction_time_risk_score"] = txn_merged["transaction_time_risk_score"].fillna(0.0)
txn_merged["retrospective_risk_score"] = txn_merged["retrospective_risk_score"].fillna(0.0)

out_path = DEST_DIR / "finguard_transactions_slim.json"
txn_merged.to_json(out_path, orient="records", date_format="iso")
print(f"  Written: {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 3. Build user analytics with risk scores
# ---------------------------------------------------------------------------
print("\n[3/7] Building user analytics with M6 risk scores...")

USER_RISK_COLS = [
    "user_id",
    "retrospective_risk_score",
    "risk_level",
    "top_risk_signal_1",
    "top_risk_signal_2",
    "top_risk_signal_3",
    "explanation",
]
user_risk_slim = user_risk[USER_RISK_COLS].rename(columns={"user_id": "user_id_normalized"})
users_merged = user_analytics.merge(user_risk_slim, on="user_id_normalized", how="left")
users_merged["kyc_status_clean"] = users_merged["kyc_status_clean"].fillna("UNKNOWN")
users_merged["risk_level"] = users_merged["risk_level"].fillna("LOW")
users_merged["explanation"] = users_merged["explanation"].fillna("")
users_merged["top_risk_signal_1"] = users_merged["top_risk_signal_1"].fillna("")
users_merged["top_risk_signal_2"] = users_merged["top_risk_signal_2"].fillna("")
users_merged["top_risk_signal_3"] = users_merged["top_risk_signal_3"].fillna("")
users_merged["kyc_match_flag"] = users_merged["kyc_match_flag"].fillna(False).astype(bool)

out_path = DEST_DIR / "users_slim.json"
users_merged.to_json(out_path, orient="records")
print(f"  Users with risk: {len(users_merged):,} | Written: {out_path} ({out_path.stat().st_size/1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 4. Build merchant analytics with risk scores
# ---------------------------------------------------------------------------
print("\n[4/7] Building merchant analytics with M6 risk scores...")

MERCHANT_RISK_COLS = [
    "merchant_id",
    "retrospective_risk_score",
    "risk_level",
    "top_risk_signal_1",
    "top_risk_signal_2",
    "top_risk_signal_3",
    "explanation",
]
merchant_risk_slim = merchant_risk[MERCHANT_RISK_COLS].rename(columns={"merchant_id": "merchant_id_normalized"})
merchants_merged = merchant_analytics.merge(merchant_risk_slim, on="merchant_id_normalized", how="left")
merchants_merged["merchant_category_clean"] = merchants_merged["merchant_category_clean"].fillna("UNKNOWN")
merchants_merged["merchant_status_clean"] = merchants_merged["merchant_status_clean"].fillna("UNKNOWN")
merchants_merged["risk_level"] = merchants_merged["risk_level"].fillna("LOW")
merchants_merged["explanation"] = merchants_merged["explanation"].fillna("")
merchants_merged["top_risk_signal_1"] = merchants_merged["top_risk_signal_1"].fillna("")
merchants_merged["top_risk_signal_2"] = merchants_merged["top_risk_signal_2"].fillna("")
merchants_merged["top_risk_signal_3"] = merchants_merged["top_risk_signal_3"].fillna("")

out_path = DEST_DIR / "merchants_slim.json"
merchants_merged.to_json(out_path, orient="records")
print(f"  Merchants with risk: {len(merchants_merged):,} | Written: {out_path} ({out_path.stat().st_size/1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 5. Build cluster data with member resolution
# ---------------------------------------------------------------------------
print("\n[5/7] Building cluster member index...")

# clusters.csv already has all needed columns
assert len(clusters) == 655, f"Expected 655 clusters, got {len(clusters)}"
assert (clusters["cluster_chargeback_rate"] <= 1.0).all(), "CRITICAL: cluster_chargeback_rate > 1.0 detected"
print(f"  Clusters: {len(clusters):,} (all chargeback_rates <= 1.0 ✓)")

# Verify CLU00604
clu604 = clusters[clusters["cluster_id"] == "CLU00604"].iloc[0]
assert clu604["cluster_chargeback_rate"] == 1.0, "CLU00604 rate mismatch"
assert clu604["chargeback_count"] == 2, "CLU00604 chargeback_count mismatch"
print(f"  CLU00604: rate={clu604['cluster_chargeback_rate']} count={clu604['chargeback_count']} ✓")

# Serialise clusters
clusters["top_signals"] = clusters["top_signals"].fillna("")
clusters["explanation"] = clusters["explanation"].fillna("")
clusters["risk_level"] = clusters["risk_level"].fillna("LOW")
out_path = DEST_DIR / "clusters_slim.json"
clusters.to_json(out_path, orient="records")
print(f"  Written: {out_path} ({out_path.stat().st_size/1024:.0f} KB)")

# Build cluster_members_map: cluster_id -> {users: [...], merchants: [...]}
users_by_cluster = cluster_members[cluster_members["node_type"] == "USER"].groupby("cluster_id")["node_id"].apply(list)
merchants_by_cluster = cluster_members[cluster_members["node_type"] == "MERCHANT"].groupby("cluster_id")["node_id"].apply(list)
cluster_ids = clusters["cluster_id"].tolist()
members_map = {}
for cid in cluster_ids:
    members_map[cid] = {
        "users": users_by_cluster.get(cid, []),
        "merchants": merchants_by_cluster.get(cid, []),
    }

out_path = DEST_DIR / "cluster_members_map.json"
with open(out_path, "w") as f:
    json.dump(members_map, f, separators=(",", ":"))
print(f"  Written: {out_path} ({out_path.stat().st_size/1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 6. Build chargeback lookup (by txn_id)
# ---------------------------------------------------------------------------
print("\n[6/7] Building chargeback lookup...")

chargebacks["txn_id_normalized"] = chargebacks["txn_id_normalized"].astype(str)
chargebacks["first_chargeback_timestamp"] = chargebacks["first_chargeback_timestamp"].fillna("").astype(str)
chargebacks["latest_chargeback_timestamp"] = chargebacks["latest_chargeback_timestamp"].fillna("").astype(str)

out_path = DEST_DIR / "chargebacks_slim.json"
chargebacks.to_json(out_path, orient="records")
print(f"  Chargebacks: {len(chargebacks):,} | Written: {out_path} ({out_path.stat().st_size/1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 7. Copy remaining supporting CSVs needed for existing tests
# ---------------------------------------------------------------------------
print("\n[7/7] Copying supporting CSVs for backward compatibility...")

src_files = [
    BASE_DIR / "finguard_transactions.csv",
    BASE_DIR / "users_analytics.csv",
    BASE_DIR / "merchants_analytics.csv",
    BASE_DIR / "chargebacks_aggregated.csv",
    BASE_DIR / "risk" / "transaction_risk_scores.csv",
    BASE_DIR / "risk" / "user_risk_scores.csv",
    BASE_DIR / "risk" / "merchant_risk_scores.csv",
    BASE_DIR / "graph" / "suspicious_clusters.csv",
    BASE_DIR / "graph" / "cluster_members.csv",
    BASE_DIR / "graph" / "user_merchant_relationships.csv",
    BASE_DIR / "features" / "transaction_risk_features.csv",
    BASE_DIR / "features" / "user_risk_features.csv",
    BASE_DIR / "features" / "merchant_risk_features.csv",
    BASE_DIR / "features" / "chargeback_risk_features.csv",
]

for f in src_files:
    if f.exists():
        dest_file = DEST_DIR / f.name
        shutil.copy2(f, dest_file)
        print(f"  Copied {f.name}")
    else:
        print(f"  WARNING: Not found: {f}")


# ---------------------------------------------------------------------------
# Final Validation Summary
# ---------------------------------------------------------------------------
print("\n=== VALIDATION SUMMARY ===")
txn_check = txn_merged
print(f"Total transactions:    {len(txn_check):,}  (expected 20,000)")
print(f"Total value:           ₹{txn_check['amount_numeric'].sum():,.2f}  (expected 239,232,643.30)")
print(f"Average value:         ₹{txn_check['amount_numeric'].sum()/len(txn_check):,.2f}  (expected 11,961.63)")
success_r = (txn_check["status_clean"] == "SUCCESS").sum() / len(txn_check)
failed_r = (txn_check["status_clean"] == "FAILED").sum() / len(txn_check)
pending_r = (txn_check["status_clean"] == "PENDING").sum() / len(txn_check)
print(f"Success rate:          {success_r*100:.2f}%  (expected 85.26%)")
print(f"Failure rate:          {failed_r*100:.2f}%  (expected 9.78%)")
print(f"Pending rate:          {pending_r*100:.2f}%  (expected 4.96%)")
cb_rate = txn_check["has_chargeback"].sum() / len(txn_check)
print(f"Chargeback rate:       {cb_rate*100:.3f}%  (expected 12.255%)")
total_disputed = txn_check["total_disputed_amount"].sum()
print(f"Total disputed:        ₹{total_disputed:,.2f}  (expected 6,342,602.86)")
disputed_ratio = total_disputed / txn_check["amount_numeric"].sum()
print(f"Disputed ratio:        {disputed_ratio*100:.4f}%  (expected 2.6512%)")
delays = txn_check["dispute_after_7_days_flag"].sum()
print(f"Disputes after 7 days: {delays:,}  (expected 1,102)")
print()
print(f"Missing UTR:           {txn_check['utr_missing_flag'].sum():,}  (expected 1,000)")
print(f"Negative amounts:      {txn_check['amount_negative_flag'].sum():,}  (expected 420)")
print(f"Unmatched KYC:         {(~txn_check['transaction_has_kyc']).sum():,}  (expected 13,522)")
print(f"Unmatched merchant:    {(~txn_check['transaction_has_merchant']).sum():,}  (expected 10,369)")
print()
print("Dashboard data preparation complete.")
