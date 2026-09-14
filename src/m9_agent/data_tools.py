import json
from pathlib import Path
from typing import Dict, List, Any

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

_txns_by_user: Dict[str, List[Dict]] = {}
_txns_by_merchant: Dict[str, List[Dict]] = {}

def load_data():
    """Load the slim JSON files into memory."""
    global _data, _txns_by_user, _txns_by_merchant
    if _data["transactions"]: return
    try:
        with open(DATA_DIR / "finguard_transactions_slim.json") as f:
            txns = json.load(f)
            _data["transactions"] = {t["txn_id_normalized"]: t for t in txns}
            for t in txns:
                if uid := t.get("user_id_normalized"):
                    _txns_by_user.setdefault(uid, []).append(t)
                if mid := t.get("merchant_id_normalized"):
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

load_data()

def _evidence(metric: str, value: Any, source: str, field: str) -> Dict[str, Any]:
    return {"metric": metric, "value": value, "source": source, "field": field}

def get_cluster(cluster_id: str) -> Dict[str, Any]:
    """Retrieve an investigation candidate cluster by ID."""
    cluster = _data["clusters"].get(cluster_id)
    if not cluster:
        return {"error": "Insufficient evidence in the available FinGuard dataset."}
        
    return {
        "entity_type": "cluster",
        "entity_id": cluster_id,
        "evidence": [
            _evidence("cluster_risk_level", cluster.get("risk_level"), "suspicious_clusters.csv", "risk_level"),
            _evidence("cluster_risk_score", cluster.get("cluster_risk_score"), "suspicious_clusters.csv", "cluster_risk_score"),
            _evidence("cluster_chargeback_rate", cluster.get("cluster_chargeback_rate"), "suspicious_clusters.csv", "cluster_chargeback_rate"),
            _evidence("chargeback_count", cluster.get("chargeback_count"), "suspicious_clusters.csv", "chargeback_count"),
            _evidence("disputed_amount_ratio", cluster.get("disputed_amount_ratio"), "suspicious_clusters.csv", "disputed_amount_ratio"),
            _evidence("n_transactions", cluster.get("n_transactions"), "suspicious_clusters.csv", "n_transactions"),
            _evidence("n_users", cluster.get("n_users"), "suspicious_clusters.csv", "n_users"),
            _evidence("n_merchants", cluster.get("n_merchants"), "suspicious_clusters.csv", "n_merchants")
        ]
    }

def get_cluster_members(cluster_id: str) -> Dict[str, Any]:
    members = _data["cluster_members_map"].get(cluster_id)
    if not members:
        return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "cluster",
        "entity_id": cluster_id,
        "evidence": [
            _evidence("users", members.get("users", []), "cluster_members_map.json", "users"),
            _evidence("merchants", members.get("merchants", []), "cluster_members_map.json", "merchants")
        ]
    }

def get_user(user_id: str) -> Dict[str, Any]:
    user = _data["users"].get(user_id)
    if not user:
        return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "user",
        "entity_id": user_id,
        "evidence": [
            _evidence("transaction_count", user.get("transaction_count"), "users_analytics.csv", "transaction_count"),
            _evidence("total_transaction_amount", user.get("total_transaction_amount"), "users_analytics.csv", "total_transaction_amount"),
            _evidence("chargeback_count", user.get("chargeback_count"), "users_analytics.csv", "chargeback_count"),
            _evidence("total_disputed_amount", user.get("total_disputed_amount"), "users_analytics.csv", "total_disputed_amount"),
            _evidence("kyc_status", user.get("kyc_status_clean"), "users_analytics.csv", "kyc_status_clean")
        ]
    }

def get_merchant(merchant_id: str) -> Dict[str, Any]:
    merchant = _data["merchants"].get(merchant_id)
    if not merchant:
        return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "merchant",
        "entity_id": merchant_id,
        "evidence": [
            _evidence("merchant_category", merchant.get("merchant_category_clean"), "merchants_analytics.csv", "merchant_category_clean"),
            _evidence("transaction_count", merchant.get("transaction_count"), "merchants_analytics.csv", "transaction_count"),
            _evidence("total_transaction_amount", merchant.get("total_transaction_amount"), "merchants_analytics.csv", "total_transaction_amount"),
            _evidence("chargeback_rate", merchant.get("chargeback_rate"), "merchants_analytics.csv", "chargeback_rate"),
            _evidence("disputed_amount_ratio", merchant.get("disputed_amount_ratio"), "merchants_analytics.csv", "disputed_amount_ratio")
        ]
    }

def get_transaction(txn_id: str) -> Dict[str, Any]:
    txn = _data["transactions"].get(txn_id)
    if not txn:
        return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "transaction",
        "entity_id": txn_id,
        "evidence": [
            _evidence("user_id", txn.get("user_id_normalized"), "finguard_transactions.csv", "user_id_normalized"),
            _evidence("merchant_id", txn.get("merchant_id_normalized"), "finguard_transactions.csv", "merchant_id_normalized"),
            _evidence("amount_numeric", txn.get("amount_numeric"), "finguard_transactions.csv", "amount_numeric"),
            _evidence("status_clean", txn.get("status_clean"), "finguard_transactions.csv", "status_clean"),
            _evidence("timestamp_clean", txn.get("timestamp_clean"), "finguard_transactions.csv", "timestamp_clean"),
            _evidence("has_chargeback", txn.get("has_chargeback"), "finguard_transactions.csv", "has_chargeback")
        ]
    }

def get_user_transactions(user_id: str, limit: int = 10) -> Dict[str, Any]:
    txns = _txns_by_user.get(user_id, [])
    if not txns: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    sorted_txns = sorted(txns, key=lambda t: (t.get("transaction_time_risk_score", 0.0), t.get("timestamp_clean", "")), reverse=True)[:limit]
    res = [{"txn_id": t["txn_id_normalized"], "amount": t.get("amount_numeric")} for t in sorted_txns]
    return {"entity_type": "user", "entity_id": user_id, "evidence": [_evidence("recent_risky_transactions", res, "finguard_transactions.csv", "multiple")]}

def get_merchant_transactions(merchant_id: str, limit: int = 10) -> Dict[str, Any]:
    txns = _txns_by_merchant.get(merchant_id, [])
    if not txns: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    sorted_txns = sorted(txns, key=lambda t: (t.get("transaction_time_risk_score", 0.0), t.get("timestamp_clean", "")), reverse=True)[:limit]
    res = [{"txn_id": t["txn_id_normalized"], "amount": t.get("amount_numeric")} for t in sorted_txns]
    return {"entity_type": "merchant", "entity_id": merchant_id, "evidence": [_evidence("recent_risky_transactions", res, "finguard_transactions.csv", "multiple")]}

def get_user_chargebacks(user_id: str) -> Dict[str, Any]:
    txns = [t for t in _txns_by_user.get(user_id, []) if t.get("has_chargeback")]
    if not txns: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    res = [{"txn_id": t["txn_id_normalized"], "chargeback_count": _data["chargebacks"].get(t["txn_id_normalized"], {}).get("chargeback_count")} for t in txns]
    return {"entity_type": "user", "entity_id": user_id, "evidence": [_evidence("chargebacked_transactions", res, "chargebacks_aggregated.csv", "multiple")]}

def get_merchant_chargebacks(merchant_id: str) -> Dict[str, Any]:
    txns = [t for t in _txns_by_merchant.get(merchant_id, []) if t.get("has_chargeback")]
    if not txns: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    res = [{"txn_id": t["txn_id_normalized"], "chargeback_count": _data["chargebacks"].get(t["txn_id_normalized"], {}).get("chargeback_count")} for t in txns]
    return {"entity_type": "merchant", "entity_id": merchant_id, "evidence": [_evidence("chargebacked_transactions", res, "chargebacks_aggregated.csv", "multiple")]}

def get_transaction_chargebacks(txn_id: str) -> Dict[str, Any]:
    cb = _data["chargebacks"].get(txn_id)
    if not cb: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "transaction", "entity_id": txn_id,
        "evidence": [
            _evidence("chargeback_count", cb.get("chargeback_count"), "chargebacks_aggregated.csv", "chargeback_count"),
            _evidence("total_disputed_amount", cb.get("total_disputed_amount"), "chargebacks_aggregated.csv", "total_disputed_amount"),
            _evidence("max_severity", cb.get("max_severity"), "chargebacks_aggregated.csv", "max_severity")
        ]
    }

def get_user_merchants(user_id: str) -> Dict[str, Any]:
    txns = _txns_by_user.get(user_id, [])
    m_set = list(set(t.get("merchant_id_normalized") for t in txns if t.get("merchant_id_normalized")))
    if not m_set: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {"entity_type": "user", "entity_id": user_id, "evidence": [_evidence("connected_merchants", m_set, "finguard_transactions.csv", "merchant_id_normalized")]}

def get_merchant_users(merchant_id: str) -> Dict[str, Any]:
    txns = _txns_by_merchant.get(merchant_id, [])
    u_set = list(set(t.get("user_id_normalized") for t in txns if t.get("user_id_normalized")))
    if not u_set: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {"entity_type": "merchant", "entity_id": merchant_id, "evidence": [_evidence("connected_users", u_set, "finguard_transactions.csv", "user_id_normalized")]}

def get_user_clusters(user_id: str) -> Dict[str, Any]:
    c_set = [cid for cid, m in _data["cluster_members_map"].items() if user_id in m.get("users", [])]
    if not c_set: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {"entity_type": "user", "entity_id": user_id, "evidence": [_evidence("suspicious_clusters", c_set, "cluster_members_map.json", "users")]}

def get_merchant_clusters(merchant_id: str) -> Dict[str, Any]:
    c_set = [cid for cid, m in _data["cluster_members_map"].items() if merchant_id in m.get("merchants", [])]
    if not c_set: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {"entity_type": "merchant", "entity_id": merchant_id, "evidence": [_evidence("suspicious_clusters", c_set, "cluster_members_map.json", "merchants")]}

def get_transaction_risk(txn_id: str) -> Dict[str, Any]:
    txn = _data["transactions"].get(txn_id)
    if not txn: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "transaction", "entity_id": txn_id,
        "evidence": [
            _evidence("transaction_time_risk_score", txn.get("transaction_time_risk_score"), "transaction_risk_scores.csv", "transaction_time_risk_score"),
            _evidence("transaction_time_risk_level", txn.get("transaction_time_risk_level"), "transaction_risk_scores.csv", "transaction_time_risk_level"),
            _evidence("retrospective_risk_score", txn.get("retrospective_risk_score"), "transaction_risk_scores.csv", "retrospective_risk_score"),
            _evidence("retrospective_risk_level", txn.get("retrospective_risk_level"), "transaction_risk_scores.csv", "retrospective_risk_level")
        ]
    }

def get_user_risk(user_id: str) -> Dict[str, Any]:
    user = _data["users"].get(user_id)
    if not user: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "user", "entity_id": user_id,
        "evidence": [
            _evidence("risk_score", user.get("retrospective_risk_score"), "user_risk_scores.csv", "retrospective_risk_score"),
            _evidence("risk_level", user.get("risk_level"), "user_risk_scores.csv", "risk_level")
        ]
    }

def get_merchant_risk(merchant_id: str) -> Dict[str, Any]:
    merchant = _data["merchants"].get(merchant_id)
    if not merchant: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "merchant", "entity_id": merchant_id,
        "evidence": [
            _evidence("risk_score", merchant.get("retrospective_risk_score"), "merchant_risk_scores.csv", "retrospective_risk_score"),
            _evidence("risk_level", merchant.get("risk_level"), "merchant_risk_scores.csv", "risk_level")
        ]
    }

def get_cluster_risk(cluster_id: str) -> Dict[str, Any]:
    cluster = _data["clusters"].get(cluster_id)
    if not cluster: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    return {
        "entity_type": "cluster", "entity_id": cluster_id,
        "evidence": [
            _evidence("risk_score", cluster.get("cluster_risk_score"), "suspicious_clusters.csv", "cluster_risk_score"),
            _evidence("risk_level", cluster.get("risk_level"), "suspicious_clusters.csv", "risk_level")
        ]
    }

def get_risk_signals(entity_type: str, entity_id: str) -> Dict[str, Any]:
    if entity_type == "cluster":
        item = _data["clusters"].get(entity_id)
        source = "suspicious_clusters.csv"
        sig_field = "top_signals"
        if item:
            signals = item.get("top_signals", "").split("|")
            explanation = item.get("explanation")
    elif entity_type == "user":
        item = _data["users"].get(entity_id)
        source = "user_risk_scores.csv"
        sig_field = "top_risk_signal"
        if item:
            signals = [item.get(f"top_risk_signal_{i}") for i in range(1,4) if item.get(f"top_risk_signal_{i}")]
            explanation = item.get("explanation")
    elif entity_type == "merchant":
        item = _data["merchants"].get(entity_id)
        source = "merchant_risk_scores.csv"
        sig_field = "top_risk_signal"
        if item:
            signals = [item.get(f"top_risk_signal_{i}") for i in range(1,4) if item.get(f"top_risk_signal_{i}")]
            explanation = item.get("explanation")
    elif entity_type == "transaction":
        item = _data["transactions"].get(entity_id)
        source = "transaction_risk_scores.csv"
        sig_field = "top_risk_signal"
        if item:
            signals = [item.get(f"top_risk_signal_{i}") for i in range(1,4) if item.get(f"top_risk_signal_{i}")]
            explanation = item.get("explanation")
    else:
        return {"error": "Unknown entity type"}
        
    if not item: return {"error": "Insufficient evidence in the available FinGuard dataset."}
    
    return {
        "entity_type": entity_type, "entity_id": entity_id,
        "evidence": [
            _evidence("risk_signals", signals, source, sig_field),
            _evidence("explanation", explanation, source, "explanation")
        ]
    }

def get_data_quality_context(entity_type: str, entity_id: str) -> Dict[str, Any]:
    if entity_type == "transaction":
        txn = _data["transactions"].get(entity_id)
        if not txn: return {"error": "Insufficient evidence in the available FinGuard dataset."}
        issues = []
        if txn.get("utr_missing_flag"): issues.append("Missing UTR")
        if txn.get("amount_negative_flag"): issues.append("Negative amount")
        if not txn.get("transaction_has_kyc"): issues.append("Missing KYC enrichment")
        if not txn.get("transaction_has_merchant"): issues.append("Missing merchant enrichment")
        return {
            "entity_type": "transaction", "entity_id": entity_id,
            "evidence": [_evidence("data_quality_issues", issues, "finguard_transactions.csv", "flags")]
        }
    return {"error": f"Data quality context not explicitly modeled for {entity_type} in slim JSONs."}

def get_top_investigation_candidates() -> Dict[str, Any]:
    clusters = list(_data["clusters"].values())
    sorted_c = sorted(clusters, key=lambda c: c.get("cluster_risk_score", 0.0), reverse=True)
    res = [{"cluster_id": c["cluster_id"], "risk_level": c.get("risk_level"), "score": c.get("cluster_risk_score")} for c in sorted_c[:5]]
    return {"entity_type": "system", "entity_id": "top_clusters", "evidence": [_evidence("top_clusters", res, "suspicious_clusters.csv", "cluster_risk_score")]}
