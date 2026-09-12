"""
Post-Cleaning Validation and Join Diagnostics.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json

from src.ingestion.loaders import load_all
from src.cleaning.ids import normalize_user_id, normalize_merchant_id, normalize_txn_id

HERE = Path(__file__).resolve().parent.parent.parent
RAW_DIR = HERE / "data" / "raw"
PROCESSED_DIR = HERE / "data" / "processed"
REPORTS_DIR = HERE / "reports"

def load_processed() -> dict[str, pd.DataFrame]:
    return {
        "transactions": pd.read_csv(PROCESSED_DIR / "transactions_clean.csv", dtype=str),
        "kyc": pd.read_csv(PROCESSED_DIR / "kyc_clean.csv", dtype=str),
        "merchants": pd.read_csv(PROCESSED_DIR / "merchants_clean.csv", dtype=str),
        "chargebacks": pd.read_csv(PROCESSED_DIR / "chargebacks_clean.csv", dtype=str)
    }

def id_validation(df: pd.DataFrame, raw_col: str, norm_col: str) -> dict:
    valid_mask = df[norm_col].notna() & (df[norm_col] != "")
    raw_unique = df.loc[valid_mask, raw_col].nunique()
    norm_unique = df.loc[valid_mask, norm_col].nunique()
    
    counts = df.loc[valid_mask].groupby(norm_col)[raw_col].nunique()
    collisions = counts[counts > 1]
    
    collision_examples = {}
    for norm_id in collisions.head(5).index:
        raw_vals = df.loc[df[norm_col] == norm_id, raw_col].dropna().unique().tolist()
        collision_examples[norm_id] = raw_vals
        
    return {
        "raw_unique": raw_unique,
        "norm_unique": norm_unique,
        "collisions_count": len(collisions),
        "collision_examples": collision_examples
    }

def match_validation(source_df, target_df, source_col, target_col):
    source_ids = set(source_df[source_col].dropna()) - {""}
    target_ids = set(target_df[target_col].dropna()) - {""}
    
    matched = len(source_ids.intersection(target_ids))
    unmatched = len(source_ids - target_ids)
    
    match_pct = (matched / len(source_ids)) * 100 if source_ids else 0
    unmatched_examples = list(source_ids - target_ids)[:20]
    
    return {
        "total_source_keys": len(source_ids),
        "matched": matched,
        "unmatched": unmatched,
        "match_pct": match_pct,
        "unmatched_examples": unmatched_examples
    }

def generate_diagnostics():
    raw_ds = load_all(RAW_DIR)
    proc_ds = load_processed()
    
    md_lines = ["# FinGuard Post-Cleaning Validation & Join Diagnostics", ""]
    diagnostics_rows = []
    
    overall_pass = True
    
    # 1. ID Normalization
    md_lines.extend(["## 1. ID Normalization Validation", ""])
    id_checks = [
        ("KYC user_id", proc_ds["kyc"], "original_user_id", "user_id_normalized"),
        ("Merchant merchant_id", proc_ds["merchants"], "original_merchant_id", "merchant_id_normalized"),
        ("Transaction txn_id", proc_ds["transactions"], "original_txn_id", "txn_id_normalized"),
        ("Chargeback complaint_id", proc_ds["chargebacks"], "original_complaint_id", "complaint_id_normalized"),
    ]
    
    for name, df, raw_col, norm_col in id_checks:
        res = id_validation(df, raw_col, norm_col)
        md_lines.append(f"### {name}")
        md_lines.append(f"- Raw unique: {res['raw_unique']}")
        md_lines.append(f"- Normalized unique: {res['norm_unique']}")
        md_lines.append(f"- Collision groups (>1 raw per norm): {res['collisions_count']}")
        if res['collision_examples']:
            md_lines.append("- Examples:")
            for k, v in res['collision_examples'].items():
                md_lines.append(f"  - {k} <- {', '.join(v)}")
        md_lines.append("")
        
    # 2. Txn -> KYC
    md_lines.extend(["## 2. Transaction -> KYC Matching", ""])
    txn_kyc = match_validation(proc_ds["transactions"], proc_ds["kyc"], "user_id_normalized", "user_id_normalized")
    md_lines.append(f"- Matched IDs: {txn_kyc['matched']}")
    md_lines.append(f"- Unmatched IDs: {txn_kyc['unmatched']}")
    md_lines.append(f"- Match %: {txn_kyc['match_pct']:.2f}%")
    md_lines.append("- Example unmatched normalized IDs:")
    md_lines.append(f"  {', '.join(txn_kyc['unmatched_examples'])}")
    md_lines.append("")
    
    for ex in txn_kyc["unmatched_examples"]:
        # Find raw values in txn
        raw_vals = proc_ds["transactions"].loc[proc_ds["transactions"]["user_id_normalized"] == ex, "original_user_id"].unique()
        diagnostics_rows.append({"join_type": "txn->kyc", "normalized_id": ex, "raw_id": raw_vals[0] if len(raw_vals) else ""})
        
    # 3. Txn -> Merchant
    md_lines.extend(["## 3. Transaction -> Merchant Matching", ""])
    txn_merch = match_validation(proc_ds["transactions"], proc_ds["merchants"], "merchant_id_normalized", "merchant_id_normalized")
    md_lines.append(f"- Matched IDs: {txn_merch['matched']}")
    md_lines.append(f"- Unmatched IDs: {txn_merch['unmatched']}")
    md_lines.append(f"- Match %: {txn_merch['match_pct']:.2f}%")
    md_lines.append("- Example unmatched normalized IDs:")
    md_lines.append(f"  {', '.join(txn_merch['unmatched_examples'])}")
    md_lines.append("")
    
    for ex in txn_merch["unmatched_examples"]:
        raw_vals = proc_ds["transactions"].loc[proc_ds["transactions"]["merchant_id_normalized"] == ex, "original_merchant_id"].unique()
        diagnostics_rows.append({"join_type": "txn->merchant", "normalized_id": ex, "raw_id": raw_vals[0] if len(raw_vals) else ""})

    # 4. Chargeback Joins
    md_lines.extend(["## 4. Chargeback Joins", ""])
    cb_txn = match_validation(proc_ds["chargebacks"], proc_ds["transactions"], "txn_id_normalized", "txn_id_normalized")
    cb_kyc = match_validation(proc_ds["chargebacks"], proc_ds["kyc"], "user_id_normalized", "user_id_normalized")
    cb_merch = match_validation(proc_ds["chargebacks"], proc_ds["merchants"], "merchant_id_normalized", "merchant_id_normalized")
    
    md_lines.append("### Chargeback -> Transaction")
    md_lines.append(f"- Match %: {cb_txn['match_pct']:.2f}% ({cb_txn['matched']} matched, {cb_txn['unmatched']} unmatched)")
    md_lines.append("### Chargeback -> KYC")
    md_lines.append(f"- Match %: {cb_kyc['match_pct']:.2f}% ({cb_kyc['matched']} matched, {cb_kyc['unmatched']} unmatched)")
    md_lines.append("### Chargeback -> Merchant")
    md_lines.append(f"- Match %: {cb_merch['match_pct']:.2f}% ({cb_merch['matched']} matched, {cb_merch['unmatched']} unmatched)")
    md_lines.append("")
    
    for ex in cb_txn["unmatched_examples"]: diagnostics_rows.append({"join_type": "cb->txn", "normalized_id": ex, "raw_id": ""})
    for ex in cb_kyc["unmatched_examples"]: diagnostics_rows.append({"join_type": "cb->kyc", "normalized_id": ex, "raw_id": ""})
    for ex in cb_merch["unmatched_examples"]: diagnostics_rows.append({"join_type": "cb->merchant", "normalized_id": ex, "raw_id": ""})
    
    # 5. Symmetry Check
    md_lines.extend(["## 5. Symmetry Check", ""])
    usr_tests = ["USR12345", "usr12345", "USR-12345", "USR 12345", "usr_12345", "12345"]
    usr_res = {t: normalize_user_id(t) for t in usr_tests}
    usr_pass = len(set(usr_res.values())) == 1
    
    mch_tests = ["MCH1234", "mch1234", "MCH-1234", "MCH 1234", "1234"]
    mch_res = {t: normalize_merchant_id(t) for t in mch_tests}
    mch_pass = len(set(mch_res.values())) == 1
    
    md_lines.append(f"- User ID symmetry pass: {usr_pass}")
    md_lines.append(f"- Merchant ID symmetry pass: {mch_pass}")
    if not usr_pass or not mch_pass: overall_pass = False
    md_lines.append("")

    # 6. Column Survival
    md_lines.extend(["## 6. Column Survival", ""])
    req_cols = {
        "transactions": ["txn_id_normalized", "user_id_normalized", "merchant_id_normalized", "amount_numeric", "timestamp_clean", "status_clean", "utr_clean", "mcc_clean"],
        "kyc": ["user_id_normalized", "pan_clean", "aadhaar_clean", "monthly_income_numeric", "city_clean", "state_clean", "occupation_clean", "kyc_status_clean"],
        "merchants": ["merchant_id_normalized", "mcc_clean", "merchant_category_clean", "merchant_status_clean", "business_type_clean"],
        "chargebacks": ["complaint_id_normalized", "txn_id_normalized", "user_id_normalized", "merchant_id_normalized", "disputed_amount_numeric", "reason_code_clean", "severity_clean", "resolution_status_clean"]
    }
    for ds, cols in req_cols.items():
        missing = [c for c in cols if c not in proc_ds[ds].columns]
        if missing:
            md_lines.append(f"- {ds}: FAIL missing {missing}")
            overall_pass = False
        else:
            md_lines.append(f"- {ds}: PASS")
    md_lines.append("")

    # 7. Data Loss
    md_lines.extend(["## 7. Data Loss Check", ""])
    expected_diff = {"transactions": 400, "kyc": 278, "merchants": 12, "chargebacks": 84}
    for ds in expected_diff:
        raw_c = len(raw_ds[ds])
        proc_c = len(proc_ds[ds])
        diff = raw_c - proc_c
        if diff == expected_diff[ds]:
            md_lines.append(f"- {ds}: PASS ({raw_c} -> {proc_c}, diff={diff})")
        else:
            md_lines.append(f"- {ds}: FAIL ({raw_c} -> {proc_c}, diff={diff}, expected={expected_diff[ds]})")
            overall_pass = False
    md_lines.append("")
    
    # 8. Negative Values Check
    md_lines.extend(["## 8. Negative Values Check", ""])
    txn_neg = proc_ds["transactions"]["amount_is_negative"].astype(str).str.lower() == "true"
    cb_neg = proc_ds["chargebacks"]["disputed_amount_is_negative"].astype(str).str.lower() == "true"
    md_lines.append(f"- Transactions with negative amount flag: {txn_neg.sum()}")
    md_lines.append(f"- Chargebacks with negative amount flag: {cb_neg.sum()}")
    if txn_neg.sum() == 0 and len(proc_ds["transactions"]) > 0: 
        md_lines.append("- WARNING: No negative amounts found in transactions, verify if expected.")
    md_lines.append("")
    
    # 9. Lineage
    md_lines.extend(["## 9. Lineage Check", ""])
    for ds, df in proc_ds.items():
        if "source_dataset" in df.columns and "source_row_number" in df.columns:
            md_lines.append(f"- {ds}: PASS")
        else:
            md_lines.append(f"- {ds}: FAIL")
            overall_pass = False
    md_lines.append("")
    
    # 10. Conclusion
    md_lines.append("## Conclusion")
    if overall_pass:
        md_lines.append("**OVERALL: PASS**")
    else:
        md_lines.append("**OVERALL: FAIL**")
        
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "post_cleaning_validation.md", "w") as f:
        f.write("\n".join(md_lines))
        
    diag_df = pd.DataFrame(diagnostics_rows)
    diag_df.to_csv(REPORTS_DIR / "join_diagnostics.csv", index=False)
    
    print("Diagnostics complete.")

if __name__ == "__main__":
    generate_diagnostics()
