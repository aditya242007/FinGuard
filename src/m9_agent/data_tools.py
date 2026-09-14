import json
from pathlib import Path
from typing import Dict, List, Any, Optional

DATA_DIR = Path("dashboard/public/data")

# In-memory storage for O(1) lookups
_data: Dict[str, Any] = {
    "transactions": {},
    "users": {},
    "merchants": {},
    "clusters": {},
    "chargebacks": {},
    "cluster_members_map": {}
}

# Indexes
_txns_by_user: Dict[str, List[Dict]] = {}
_txns_by_merchant: Dict[str, List[Dict]] = {}

def load_data():
    """Load the slim JSON files into memory."""
    global _data, _txns_by_user, _txns_by_merchant
    
    if _data["transactions"]:
        return # Already loaded
        
    try:
        with open(DATA_DIR / "finguard_transactions_slim.json") as f:
            txns = json.load(f)
            _data["transactions"] = {t["txn_id_normalized"]: t for t in txns}
            
            for t in txns:
                uid = t.get("user_id_normalized")
                mid = t.get("merchant_id_normalized")
                if uid:
                    _txns_by_user.setdefault(uid, []).append(t)
                if mid:
                    _txns_by_merchant.setdefault(mid, []).append(t)
                    
        with open(DATA_DIR / "users_slim.json") as f:
            users = json.load(f)
            _data["users"] = {u["user_id_normalized"]: u for u in users}
            
        with open(DATA_DIR / "merchants_slim.json") as f:
            merchants = json.load(f)
            _data["merchants"] = {m["merchant_id_normalized"]: m for m in merchants}
            
        with open(DATA_DIR / "clusters_slim.json") as f:
            clusters = json.load(f)
            _data["clusters"] = {c["cluster_id"]: c for c in clusters}
            
        with open(DATA_DIR / "chargebacks_slim.json") as f:
            chargebacks = json.load(f)
            _data["chargebacks"] = {cb["txn_id_normalized"]: cb for cb in chargebacks}
            
        with open(DATA_DIR / "cluster_members_map.json") as f:
            _data["cluster_members_map"] = json.load(f)
            
    except Exception as e:
        print(f"Error loading data: {e}")
        # In a real scenario we'd raise, but we want tools to gracefully fail if files are missing.

# Ensure data is loaded on import
load_data()

def _add_provenance(data: Dict, source: str) -> Dict:
    """Helper to add provenance if needed, though for the LLM keeping it flat might be better.
       We will follow the phase 4 request by adding source information.
    """
    res = {"evidence": data, "provenance": {"source": source}}
    return res

def get_cluster(cluster_id: str) -> Dict[str, Any]:
    """Retrieve an investigation candidate cluster by ID."""
    cluster = _data["clusters"].get(cluster_id)
    if not cluster:
        return {"error": f"Cluster {cluster_id} not found. Insufficient evidence in the available dataset."}
        
    return {
        "cluster_id": cluster["cluster_id"],
        "risk_level": cluster.get("risk_level"),
        "cluster_risk_score": cluster.get("cluster_risk_score"),
        "cluster_chargeback_rate": cluster.get("cluster_chargeback_rate"),
        "chargeback_count": cluster.get("chargeback_count"),
        "disputed_amount_ratio": cluster.get("disputed_amount_ratio"),
        "top_signals": cluster.get("top_signals"),
        "explanation": cluster.get("explanation"),
        "n_users": cluster.get("n_users"),
        "n_merchants": cluster.get("n_merchants"),
        "n_transactions": cluster.get("n_transactions"),
        "_provenance": {"source": "suspicious_clusters.csv"}
    }

def get_cluster_members(cluster_id: str) -> Dict[str, Any]:
    """Retrieve users and merchants associated with a cluster."""
    members = _data["cluster_members_map"].get(cluster_id)
    if not members:
        return {"error": f"Members for cluster {cluster_id} not found."}
    
    return {
        "cluster_id": cluster_id,
        "users": members.get("users", []),
        "merchants": members.get("merchants", []),
        "_provenance": {"source": "cluster_members_map.json"}
    }

def get_user(user_id: str) -> Dict[str, Any]:
    """Retrieve a user profile and their retrospective risk score."""
    user = _data["users"].get(user_id)
    if not user:
        return {"error": f"User {user_id} not found. Insufficient evidence in the available dataset."}
        
    return {
        "user_id": user["user_id_normalized"],
        "transaction_count": user.get("transaction_count"),
        "total_transaction_amount": user.get("total_transaction_amount"),
        "chargeback_count": user.get("chargeback_count"),
        "total_disputed_amount": user.get("total_disputed_amount"),
        "kyc_status_clean": user.get("kyc_status_clean"),
        "risk_level": user.get("risk_level"),
        "retrospective_risk_score": user.get("retrospective_risk_score"),
        "explanation": user.get("explanation"),
        "top_signals": [user.get(f"top_risk_signal_{i}") for i in range(1, 4) if user.get(f"top_risk_signal_{i}")],
        "_provenance": {"source": "users_analytics.csv"}
    }

def get_merchant(merchant_id: str) -> Dict[str, Any]:
    """Retrieve a merchant profile and their retrospective risk score."""
    merchant = _data["merchants"].get(merchant_id)
    if not merchant:
        return {"error": f"Merchant {merchant_id} not found. Insufficient evidence in the available dataset."}
        
    return {
        "merchant_id": merchant["merchant_id_normalized"],
        "merchant_category_clean": merchant.get("merchant_category_clean"),
        "merchant_status_clean": merchant.get("merchant_status_clean"),
        "transaction_count": merchant.get("transaction_count"),
        "total_transaction_amount": merchant.get("total_transaction_amount"),
        "chargeback_rate": merchant.get("chargeback_rate"),
        "disputed_amount_ratio": merchant.get("disputed_amount_ratio"),
        "risk_level": merchant.get("risk_level"),
        "retrospective_risk_score": merchant.get("retrospective_risk_score"),
        "explanation": merchant.get("explanation"),
        "top_signals": [merchant.get(f"top_risk_signal_{i}") for i in range(1, 4) if merchant.get(f"top_risk_signal_{i}")],
        "_provenance": {"source": "merchants_analytics.csv"}
    }

def get_transaction(txn_id: str) -> Dict[str, Any]:
    """Retrieve transaction details including transaction-time risk."""
    txn = _data["transactions"].get(txn_id)
    if not txn:
        return {"error": f"Transaction {txn_id} not found. Insufficient evidence in the available dataset."}
        
    return {
        "txn_id": txn["txn_id_normalized"],
        "user_id": txn.get("user_id_normalized"),
        "merchant_id": txn.get("merchant_id_normalized"),
        "amount_numeric": txn.get("amount_numeric"),
        "status_clean": txn.get("status_clean"),
        "timestamp_clean": txn.get("timestamp_clean"),
        "has_chargeback": txn.get("has_chargeback"),
        "transaction_time_risk_level": txn.get("transaction_time_risk_level"),
        "transaction_time_risk_score": txn.get("transaction_time_risk_score"),
        "retrospective_risk_level": txn.get("retrospective_risk_level"),
        "explanation": txn.get("explanation"),
        "top_signals": [txn.get(f"top_risk_signal_{i}") for i in range(1, 4) if txn.get(f"top_risk_signal_{i}")],
        "data_quality_issues": {
            "utr_missing": txn.get("utr_missing_flag"),
            "amount_negative": txn.get("amount_negative_flag"),
            "no_kyc_match": not txn.get("transaction_has_kyc"),
            "no_merchant_match": not txn.get("transaction_has_merchant")
        },
        "_provenance": {"source": "finguard_transactions.csv"}
    }

def get_user_transactions(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Retrieve top recent/risky transactions for a user."""
    txns = _txns_by_user.get(user_id, [])
    if not txns:
        return {"error": f"No transactions found for user {user_id}."}
        
    # Sort by risk score descending, then timestamp descending
    sorted_txns = sorted(txns, key=lambda t: (t.get("transaction_time_risk_score", 0.0), t.get("timestamp_clean", "")), reverse=True)
    
    result = []
    for t in sorted_txns[:limit]:
        result.append({
            "txn_id": t["txn_id_normalized"],
            "merchant_id": t.get("merchant_id_normalized"),
            "amount_numeric": t.get("amount_numeric"),
            "has_chargeback": t.get("has_chargeback"),
            "transaction_time_risk_level": t.get("transaction_time_risk_level")
        })
        
    return {
        "user_id": user_id,
        "total_transactions": len(txns),
        "returned_transactions": len(result),
        "transactions": result,
        "_provenance": {"source": "finguard_transactions.csv"}
    }

def get_merchant_transactions(merchant_id: str, limit: int = 10) -> Dict[str, Any]:
    """Retrieve top recent/risky transactions for a merchant."""
    txns = _txns_by_merchant.get(merchant_id, [])
    if not txns:
        return {"error": f"No transactions found for merchant {merchant_id}."}
        
    sorted_txns = sorted(txns, key=lambda t: (t.get("transaction_time_risk_score", 0.0), t.get("timestamp_clean", "")), reverse=True)
    
    result = []
    for t in sorted_txns[:limit]:
        result.append({
            "txn_id": t["txn_id_normalized"],
            "user_id": t.get("user_id_normalized"),
            "amount_numeric": t.get("amount_numeric"),
            "has_chargeback": t.get("has_chargeback"),
            "transaction_time_risk_level": t.get("transaction_time_risk_level")
        })
        
    return {
        "merchant_id": merchant_id,
        "total_transactions": len(txns),
        "returned_transactions": len(result),
        "transactions": result,
        "_provenance": {"source": "finguard_transactions.csv"}
    }

def get_user_chargebacks(user_id: str) -> Dict[str, Any]:
    """Retrieve all chargebacks filed by a specific user."""
    txns = _txns_by_user.get(user_id, [])
    cb_txns = [t for t in txns if t.get("has_chargeback")]
    
    if not cb_txns:
        return {"message": f"No chargebacks found for user {user_id}."}
        
    results = []
    for t in cb_txns:
        tid = t["txn_id_normalized"]
        cb = _data["chargebacks"].get(tid)
        if cb:
            results.append({
                "txn_id": tid,
                "merchant_id": t.get("merchant_id_normalized"),
                "chargeback_count": cb.get("chargeback_count"),
                "total_disputed_amount": cb.get("total_disputed_amount"),
                "max_severity": cb.get("max_severity")
            })
            
    return {
        "user_id": user_id,
        "total_chargebacked_transactions": len(results),
        "chargebacks": results,
        "_provenance": {"source": "chargebacks_aggregated.csv"}
    }

def get_top_investigation_candidates(entity_type: str = "cluster", limit: int = 5) -> Dict[str, Any]:
    """Retrieve top N highest risk entities of a given type ('cluster', 'user', 'merchant')."""
    if entity_type == "cluster":
        clusters = list(_data["clusters"].values())
        sorted_c = sorted(clusters, key=lambda c: c.get("cluster_risk_score", 0.0), reverse=True)
        res = [{"cluster_id": c["cluster_id"], "risk_level": c.get("risk_level"), "score": c.get("cluster_risk_score")} for c in sorted_c[:limit]]
        return {"entity_type": "cluster", "candidates": res, "_provenance": {"source": "suspicious_clusters.csv"}}
        
    elif entity_type == "user":
        users = list(_data["users"].values())
        sorted_u = sorted(users, key=lambda u: u.get("retrospective_risk_score", 0.0), reverse=True)
        res = [{"user_id": u["user_id_normalized"], "risk_level": u.get("risk_level"), "score": u.get("retrospective_risk_score")} for u in sorted_u[:limit]]
        return {"entity_type": "user", "candidates": res, "_provenance": {"source": "user_risk_scores.csv"}}
        
    elif entity_type == "merchant":
        merchants = list(_data["merchants"].values())
        sorted_m = sorted(merchants, key=lambda m: m.get("retrospective_risk_score", 0.0), reverse=True)
        res = [{"merchant_id": m["merchant_id_normalized"], "risk_level": m.get("risk_level"), "score": m.get("retrospective_risk_score")} for m in sorted_m[:limit]]
        return {"entity_type": "merchant", "candidates": res, "_provenance": {"source": "merchant_risk_scores.csv"}}
        
    return {"error": f"Unknown entity type: {entity_type}. Use 'cluster', 'user', or 'merchant'."}
