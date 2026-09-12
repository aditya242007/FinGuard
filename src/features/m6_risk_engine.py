import pandas as pd
import numpy as np
import os
import argparse

def get_signal_registry():
    """
    Returns the signal registry for M6 Risk Engine.
    """
    return {
        "transaction_time": {
            "missing_utr": {"weight": 15, "direction": 1},
            "invalid_timestamp": {"weight": 10, "direction": 1},
            "kyc_rejected_unverified": {"weight": 25, "direction": 1},
            "amount_anomaly_user_relative": {"weight": 25, "direction": 1},
            "historical_user_failure_rate": {"weight": 25, "direction": 1},
        },
        "retrospective": {
            "user_chargeback_rate": {"weight": 35, "direction": 1},
            "merchant_chargeback_rate": {"weight": 35, "direction": 1},
            "merchant_disputed_amount_ratio": {"weight": 25, "direction": 1},
            "user_delayed_dispute_rate": {"weight": 15, "direction": 1},
            "merchant_delayed_dispute_rate": {"weight": 15, "direction": 1},
            "kyc_duplicate_entity": {"weight": 10, "direction": 1},
            "user_failure_rate": {"weight": 15, "direction": 1},
            "merchant_failure_rate": {"weight": 15, "direction": 1}
        }
    }

def calculate_point_in_time_features(df):
    """
    Calculate point-in-time historical features to prevent leakage.
    Sorts by time, then computes expanding metrics.
    """
    df = df.copy()
    # Ensure sorted by time
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df = df.sort_values(["transaction_date", "txn_id_normalized"])
    
    # 1. Point-in-time historical user failure rate
    # Need to shift by 1 to not include the current transaction
    df["_is_failed"] = df["failed_flag"].astype(int)
    
    df["historical_user_failure_rate"] = df.groupby("user_id_normalized")["_is_failed"].transform(
        lambda x: x.shift(1).expanding().mean()
    ).fillna(0.0)
    
    # Calculate N for cold-start (prior transactions)
    df["historical_user_txn_count"] = df.groupby("user_id_normalized").cumcount()
    
    # 2. Point-in-time user relative amount anomaly
    # mean and std of prior transactions
    df["historical_user_amount_mean"] = df.groupby("user_id_normalized")["amount_abs"].transform(
        lambda x: x.shift(1).expanding().mean()
    )
    df["historical_user_amount_std"] = df.groupby("user_id_normalized")["amount_abs"].transform(
        lambda x: x.shift(1).expanding().std()
    )
    
    # Z-score based anomaly
    df["amount_anomaly_user_relative"] = 0.0
    valid_mask = (df["historical_user_txn_count"] >= 5) & (df["historical_user_amount_std"] > 0)
    
    z_scores = (df.loc[valid_mask, "amount_abs"] - df.loc[valid_mask, "historical_user_amount_mean"]) / df.loc[valid_mask, "historical_user_amount_std"]
    
    # Normalize z-score to 0-1 (e.g. z=0 -> 0, z>=3 -> 1)
    # Clip between 0 and 3, divide by 3
    normalized_anomaly = (z_scores.clip(lower=0, upper=3) / 3.0).fillna(0.0)
    df.loc[valid_mask, "amount_anomaly_user_relative"] = normalized_anomaly
    
    # Clean up temp cols
    df = df.drop(columns=["_is_failed", "historical_user_amount_mean", "historical_user_amount_std"])
    
    return df

def generate_explanations(row, signal_contributions, prefix=""):
    """
    Generates top signals and explanation text based on contributions.
    """
    # Filter non-zero contributions
    contribs = {k.replace(prefix, ""): v for k, v in row.items() if k in signal_contributions and v > 0}
    
    if not contribs:
        return "No risk signals identified.", [], 0.0
    
    # Sort by contribution
    sorted_contribs = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
    
    top_signals = [k.replace('_contrib', '') for k, v in sorted_contribs[:3]]
    
    # Build explanation
    exp = f"Elevated risk driven primarily by {top_signals[0].replace('_', ' ')}" if top_signals else "No risk signals identified."
    if len(top_signals) > 1:
        exp += f", combined with {top_signals[1].replace('_', ' ')}"
    if len(top_signals) > 2:
        exp += f" and {top_signals[2].replace('_', ' ')}."
    elif top_signals:
        exp += "."
        
    # sum of contributions
    total_score = sum(v for k, v in sorted_contribs)
    
    return exp, top_signals, total_score

def get_risk_level(score):
    if pd.isna(score): return "LOW"
    if score >= 80: return "CRITICAL"
    if score >= 60: return "HIGH"
    if score >= 30: return "MEDIUM"
    return "LOW"

def score_transactions(txns, user_features):
    """
    Computes transaction-time and retrospective scores for each transaction.
    """
    registry = get_signal_registry()
    tt_signals = registry["transaction_time"]
    retro_signals = registry["retrospective"]
    
    # Merge user KYC status to txns
    user_kyc = user_features[["user_id_normalized", "kyc_status", "kyc_duplicate_entity_flag"]].copy()
    txns = txns.merge(user_kyc, on="user_id_normalized", how="left")
    
    txns = calculate_point_in_time_features(txns)
    
    # Setup Transaction-Time components
    txns["tt_missing_utr_contrib"] = txns["missing_utr_flag"].fillna(False).astype(int) * tt_signals["missing_utr"]["weight"]
    txns["tt_invalid_timestamp_contrib"] = txns["timestamp_invalid_flag"].fillna(False).astype(int) * tt_signals["invalid_timestamp"]["weight"]
    
    # KYC Rejected/Unverified
    is_kyc_bad = txns["kyc_status"].isin(["REJECTED", "UNVERIFIED"]).astype(int)
    txns["tt_kyc_rejected_unverified_contrib"] = is_kyc_bad * tt_signals["kyc_rejected_unverified"]["weight"]
    
    # Historical failure rate (already 0-1)
    # Apply cold-start penalty N/5 if N<5
    cold_start_factor = (txns["historical_user_txn_count"] / 5.0).clip(upper=1.0)
    txns["tt_historical_user_failure_rate_contrib"] = txns["historical_user_failure_rate"] * cold_start_factor * tt_signals["historical_user_failure_rate"]["weight"]
    
    txns["tt_amount_anomaly_user_relative_contrib"] = txns["amount_anomaly_user_relative"] * tt_signals["amount_anomaly_user_relative"]["weight"]
    
    tt_contrib_cols = [c for c in txns.columns if c.startswith("tt_") and c.endswith("_contrib")]
    
    # Normalize TT score to 100
    tt_max_possible = sum(s["weight"] for s in tt_signals.values())
    
    # Explanations for TT
    txns["transaction_time_risk_score"] = 0.0
    txns["transaction_time_risk_level"] = "LOW"
    txns["tt_explanation"] = ""
    txns["tt_top_signals"] = None
    
    tt_scores = []
    tt_levels = []
    tt_exps = []
    tt_tops = []
    
    for idx, row in txns.iterrows():
        exp, tops, score_sum = generate_explanations(row, tt_contrib_cols, prefix="tt_")
        final_score = (score_sum / tt_max_possible) * 100.0 if tt_max_possible > 0 else 0.0
        tt_scores.append(min(100.0, final_score))
        tt_levels.append(get_risk_level(min(100.0, final_score)))
        tt_exps.append(exp)
        tt_tops.append(tops)
        
    txns["transaction_time_risk_score"] = tt_scores
    txns["transaction_time_risk_level"] = tt_levels
    txns["tt_explanation"] = tt_exps
    txns["tt_top_signals"] = tt_tops
    
    return txns

def score_users(users):
    """
    Computes retrospective scores for users.
    """
    registry = get_signal_registry()
    retro_signals = registry["retrospective"]
    
    users = users.copy()
    
    # Normalizations
    cb_rate = users["chargeback_rate"].fillna(0.0)
    users["retro_user_chargeback_rate_contrib"] = cb_rate * retro_signals["user_chargeback_rate"]["weight"]
    
    fail_rate = users["failure_rate"].fillna(0.0)
    users["retro_user_failure_rate_contrib"] = fail_rate * retro_signals["user_failure_rate"]["weight"]
    
    del_disp_rate = users["dispute_after_7_days_rate"].fillna(0.0)
    users["retro_user_delayed_dispute_rate_contrib"] = del_disp_rate * retro_signals["user_delayed_dispute_rate"]["weight"]
    
    kyc_dup = users["kyc_duplicate_entity_flag"].fillna(False).astype(int)
    users["retro_kyc_duplicate_entity_contrib"] = kyc_dup * retro_signals["kyc_duplicate_entity"]["weight"]
    
    retro_contrib_cols = [c for c in users.columns if c.startswith("retro_") and c.endswith("_contrib")]
    
    retro_max_possible = retro_signals["user_chargeback_rate"]["weight"] + \
                         retro_signals["user_failure_rate"]["weight"] + \
                         retro_signals["user_delayed_dispute_rate"]["weight"] + \
                         retro_signals["kyc_duplicate_entity"]["weight"]
                         
    scores = []
    levels = []
    exps = []
    tops = []
    
    for idx, row in users.iterrows():
        exp, tops_list, score_sum = generate_explanations(row, retro_contrib_cols, prefix="retro_")
        
        # apply cold start penalty to total score
        score_sum = score_sum * row["transaction_count"] / 5.0 if row["transaction_count"] < 5 else score_sum
        
        final_score = (score_sum / retro_max_possible) * 100.0 if retro_max_possible > 0 else 0.0
        scores.append(min(100.0, final_score))
        levels.append(get_risk_level(min(100.0, final_score)))
        exps.append(exp)
        tops.append(tops_list)
        
    users["retrospective_risk_score"] = scores
    users["risk_level"] = levels
    users["explanation"] = exps
    
    # Add top signals
    users["top_risk_signal_1"] = [t[0] if len(t) > 0 else None for t in tops]
    users["top_risk_signal_2"] = [t[1] if len(t) > 1 else None for t in tops]
    users["top_risk_signal_3"] = [t[2] if len(t) > 2 else None for t in tops]
    
    return users

def score_merchants(merchants):
    """
    Computes retrospective scores for merchants.
    """
    registry = get_signal_registry()
    retro_signals = registry["retrospective"]
    
    merchants = merchants.copy()
    
    cb_rate = merchants["chargeback_rate"].fillna(0.0)
    merchants["retro_merchant_chargeback_rate_contrib"] = cb_rate * retro_signals["merchant_chargeback_rate"]["weight"]
    
    disp_ratio = merchants["disputed_amount_ratio"].fillna(0.0)
    merchants["retro_merchant_disputed_amount_ratio_contrib"] = disp_ratio * retro_signals["merchant_disputed_amount_ratio"]["weight"]
    
    fail_rate = merchants["failure_rate"].fillna(0.0)
    merchants["retro_merchant_failure_rate_contrib"] = fail_rate * retro_signals["merchant_failure_rate"]["weight"]
    
    del_disp_rate = merchants["dispute_after_7_days_rate"].fillna(0.0)
    merchants["retro_merchant_delayed_dispute_rate_contrib"] = del_disp_rate * retro_signals["merchant_delayed_dispute_rate"]["weight"]
    
    retro_contrib_cols = [c for c in merchants.columns if c.startswith("retro_") and c.endswith("_contrib")]
    
    retro_max_possible = retro_signals["merchant_chargeback_rate"]["weight"] + \
                         retro_signals["merchant_disputed_amount_ratio"]["weight"] + \
                         retro_signals["merchant_failure_rate"]["weight"] + \
                         retro_signals["merchant_delayed_dispute_rate"]["weight"]
                         
    scores = []
    levels = []
    exps = []
    tops = []
    
    for idx, row in merchants.iterrows():
        exp, tops_list, score_sum = generate_explanations(row, retro_contrib_cols, prefix="retro_")
        
        score_sum = score_sum * row["transaction_count"] / 5.0 if row["transaction_count"] < 5 else score_sum
        
        final_score = (score_sum / retro_max_possible) * 100.0 if retro_max_possible > 0 else 0.0
        scores.append(min(100.0, final_score))
        levels.append(get_risk_level(min(100.0, final_score)))
        exps.append(exp)
        tops.append(tops_list)
        
    merchants["retrospective_risk_score"] = scores
    merchants["risk_level"] = levels
    merchants["explanation"] = exps
    
    # Add top signals
    merchants["top_risk_signal_1"] = [t[0] if len(t) > 0 else None for t in tops]
    merchants["top_risk_signal_2"] = [t[1] if len(t) > 1 else None for t in tops]
    merchants["top_risk_signal_3"] = [t[2] if len(t) > 2 else None for t in tops]
    
    return merchants

def run_risk_engine(txns_path, users_path, merchants_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    txns = pd.read_csv(txns_path)
    users = pd.read_csv(users_path)
    merchants = pd.read_csv(merchants_path)
    
    # Score Users and Merchants first to get their retro scores
    scored_users = score_users(users)
    scored_merchants = score_merchants(merchants)
    
    # Score Transactions
    scored_txns = score_transactions(txns, users)
    
    # Now map user and merchant retrospective scores to transactions
    u_retro = scored_users[["user_id_normalized", "retrospective_risk_score"]].rename(
        columns={"retrospective_risk_score": "user_retro_score"}
    )
    m_retro = scored_merchants[["merchant_id_normalized", "retrospective_risk_score"]].rename(
        columns={"retrospective_risk_score": "merchant_retro_score"}
    )
    
    scored_txns = scored_txns.merge(u_retro, on="user_id_normalized", how="left")
    scored_txns = scored_txns.merge(m_retro, on="merchant_id_normalized", how="left")
    
    # Transaction Retro score = max of user and merchant retro score
    scored_txns["retrospective_risk_score"] = scored_txns[["user_retro_score", "merchant_retro_score"]].max(axis=1).fillna(0.0)
    scored_txns["retrospective_risk_level"] = scored_txns["retrospective_risk_score"].apply(get_risk_level)
    
    # Finalize columns
    txns_out = scored_txns[[
        "txn_id_normalized", "transaction_date", "amount_abs",
        "transaction_time_risk_score", "transaction_time_risk_level",
        "retrospective_risk_score", "retrospective_risk_level",
        "tt_top_signals", "tt_explanation"
    ]].rename(columns={"tt_explanation": "explanation", "txn_id_normalized": "txn_id"})
    
    txns_out["top_risk_signal_1"] = txns_out["tt_top_signals"].apply(lambda x: x[0] if x and len(x) > 0 else None)
    txns_out["top_risk_signal_2"] = txns_out["tt_top_signals"].apply(lambda x: x[1] if x and len(x) > 1 else None)
    txns_out["top_risk_signal_3"] = txns_out["tt_top_signals"].apply(lambda x: x[2] if x and len(x) > 2 else None)
    txns_out = txns_out.drop(columns=["tt_top_signals"])
    
    users_out = scored_users[[
        "user_id_normalized", "retrospective_risk_score", "risk_level",
        "transaction_count", "total_transaction_amount", "chargeback_rate",
        "total_disputed_amount", "top_risk_signal_1", "top_risk_signal_2",
        "top_risk_signal_3", "explanation"
    ]].rename(columns={"user_id_normalized": "user_id"})
    
    merchants_out = scored_merchants[[
        "merchant_id_normalized", "retrospective_risk_score", "risk_level",
        "transaction_count", "total_transaction_amount", "chargeback_transaction_count",
        "chargeback_rate", "disputed_amount_ratio",
        "top_risk_signal_1", "top_risk_signal_2",
        "top_risk_signal_3", "explanation"
    ]].rename(columns={"merchant_id_normalized": "merchant_id"})
    
    # Save
    txns_out.to_csv(os.path.join(output_dir, "transaction_risk_scores.csv"), index=False)
    users_out.to_csv(os.path.join(output_dir, "user_risk_scores.csv"), index=False)
    merchants_out.to_csv(os.path.join(output_dir, "merchant_risk_scores.csv"), index=False)
    
    print("M6 Risk Engine scoring complete.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--txns", default="data/processed/features/transaction_risk_features.csv")
    parser.add_argument("--users", default="data/processed/features/user_risk_features.csv")
    parser.add_argument("--merchants", default="data/processed/features/merchant_risk_features.csv")
    parser.add_argument("--out", default="data/processed/risk")
    
    args = parser.parse_args()
    run_risk_engine(args.txns, args.users, args.merchants, args.out)
