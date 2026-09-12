"""
M7 — Suspicious Transaction Networks
======================================
Graph-based investigation layer for FinGuard.
Uses pandas + NetworkX only. No external database.
Reproducible deterministic pipeline.

IMPORTANT: This tool identifies behavioural patterns and
investigation candidates. It does NOT confirm fraud.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import networkx as nx

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_PROC = ROOT / "data" / "processed"
GRAPH_DIR = DATA_PROC / "graph"
RISK_DIR = DATA_PROC / "risk"
REPORTS_DIR = ROOT / "reports"

GRAPH_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 0. Data Loading
# ---------------------------------------------------------------------------

def load_inputs() -> dict[str, pd.DataFrame]:
    """Load all M3/M5/M6 outputs needed for the graph."""
    txns = pd.read_csv(DATA_PROC / "finguard_transactions.csv", low_memory=False)
    cb   = pd.read_csv(DATA_PROC / "chargebacks_clean.csv", low_memory=False)
    txn_risk = pd.read_csv(RISK_DIR / "transaction_risk_scores.csv")
    user_risk = pd.read_csv(RISK_DIR / "user_risk_scores.csv")
    merch_risk = pd.read_csv(RISK_DIR / "merchant_risk_scores.csv")
    return dict(txns=txns, cb=cb, txn_risk=txn_risk,
                user_risk=user_risk, merch_risk=merch_risk)


# ---------------------------------------------------------------------------
# 1. Node Construction
# ---------------------------------------------------------------------------

def build_user_nodes(user_risk: pd.DataFrame) -> pd.DataFrame:
    """Build USER node records from M6 user risk scores."""
    df = user_risk.rename(columns={
        "user_id": "node_id",
        "retrospective_risk_score": "risk_score",
    }).copy()
    df["node_type"] = "USER"
    df = df[["node_id", "node_type", "risk_score", "risk_level",
             "transaction_count", "total_transaction_amount",
             "chargeback_rate", "total_disputed_amount"]].copy()
    return df


def build_merchant_nodes(merch_risk: pd.DataFrame) -> pd.DataFrame:
    """Build MERCHANT node records from M6 merchant risk scores."""
    df = merch_risk.rename(columns={
        "merchant_id": "node_id",
        "retrospective_risk_score": "risk_score",
    }).copy()
    df["node_type"] = "MERCHANT"
    df = df[["node_id", "node_type", "risk_score", "risk_level",
             "transaction_count", "total_transaction_amount",
             "chargeback_transaction_count", "chargeback_rate",
             "disputed_amount_ratio"]].copy()
    return df


def build_transaction_nodes(txn_risk: pd.DataFrame) -> pd.DataFrame:
    """Build TRANSACTION node records from M6 transaction risk scores."""
    df = txn_risk.rename(columns={
        "txn_id": "node_id",
    }).copy()
    df["node_type"] = "TRANSACTION"
    # Use transaction-time score as primary; retrospective as secondary
    df = df[["node_id", "node_type",
             "transaction_time_risk_score",
             "retrospective_risk_score",
             "transaction_time_risk_level",
             "amount_abs"]].copy()
    df = df.rename(columns={
        "transaction_time_risk_score": "risk_score",
        "transaction_time_risk_level": "risk_level",
    })
    return df


def build_chargeback_nodes(cb: pd.DataFrame) -> pd.DataFrame:
    """Build CHARGEBACK node records from clean chargebacks."""
    # Normalise severity labels
    sev_map = {
        "P1": "CRITICAL", "CRIT": "CRITICAL", "CRITICAL": "CRITICAL",
        "P2": "HIGH",     "H": "HIGH",         "HIGH": "HIGH",
        "P3": "MEDIUM",   "M": "MEDIUM",       "MEDIUM": "MEDIUM",
        "P4": "LOW",      "L": "LOW",           "LOW": "LOW",
    }
    df = cb[["complaint_id_normalized", "disputed_amount_numeric",
             "severity_clean", "reason_code_clean",
             "resolution_status_clean"]].copy()
    df = df.rename(columns={
        "complaint_id_normalized": "node_id",
        "disputed_amount_numeric": "disputed_amount",
        "severity_clean": "severity",
        "reason_code_clean": "reason",
        "resolution_status_clean": "resolution_status",
    })
    df["node_type"] = "CHARGEBACK"
    df["severity_normalised"] = df["severity"].map(sev_map).fillna(df["severity"])
    # Risk score proxy: CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25, unknown=25
    sev_score = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}
    df["risk_score"] = df["severity_normalised"].map(sev_score).fillna(25)
    df["risk_level"] = df["severity_normalised"].map(
        lambda s: s if s in sev_score else "LOW"
    )
    df = df[["node_id", "node_type", "risk_score", "risk_level",
             "disputed_amount", "severity_normalised", "reason",
             "resolution_status"]].copy()
    return df


def build_all_nodes(data: dict) -> pd.DataFrame:
    user_nodes  = build_user_nodes(data["user_risk"])
    merch_nodes = build_merchant_nodes(data["merch_risk"])
    txn_nodes   = build_transaction_nodes(data["txn_risk"])
    cb_nodes    = build_chargeback_nodes(data["cb"])

    nodes = pd.concat([user_nodes, merch_nodes, txn_nodes, cb_nodes],
                      axis=0, ignore_index=True, sort=False)
    nodes = nodes.drop_duplicates(subset=["node_id"])
    return nodes.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Edge Construction
# ---------------------------------------------------------------------------

def build_performed_edges(txns: pd.DataFrame) -> pd.DataFrame:
    """USER -[PERFORMED]-> TRANSACTION"""
    edges = txns[["user_id_normalized", "txn_id_normalized",
                  "amount_numeric", "status_clean"]].copy()
    edges.columns = ["source", "target", "amount", "status"]
    edges["edge_type"] = "PERFORMED"
    edges["transaction_count"] = 1
    edges["total_amount"] = edges["amount"].abs()
    edges["chargeback_count"] = 0
    edges["disputed_amount"] = 0.0
    return edges[["source", "target", "edge_type",
                  "transaction_count", "total_amount",
                  "chargeback_count", "disputed_amount"]].copy()


def build_at_merchant_edges(txns: pd.DataFrame) -> pd.DataFrame:
    """TRANSACTION -[AT_MERCHANT]-> MERCHANT"""
    edges = txns[["txn_id_normalized", "merchant_id_normalized",
                  "amount_numeric"]].copy()
    edges.columns = ["source", "target", "amount"]
    edges["edge_type"] = "AT_MERCHANT"
    edges["transaction_count"] = 1
    edges["total_amount"] = edges["amount"].abs()
    edges["chargeback_count"] = 0
    edges["disputed_amount"] = 0.0
    return edges[["source", "target", "edge_type",
                  "transaction_count", "total_amount",
                  "chargeback_count", "disputed_amount"]].copy()


def build_has_chargeback_edges(txns: pd.DataFrame,
                               cb: pd.DataFrame) -> pd.DataFrame:
    """TRANSACTION -[HAS_CHARGEBACK]-> CHARGEBACK"""
    cb_map = cb[["txn_id_normalized", "complaint_id_normalized",
                 "disputed_amount_numeric"]].copy()
    cb_map = cb_map.rename(columns={
        "txn_id_normalized": "source",
        "complaint_id_normalized": "target",
        "disputed_amount_numeric": "disputed_amount",
    })
    cb_map["edge_type"] = "HAS_CHARGEBACK"
    cb_map["transaction_count"] = 1
    cb_map["total_amount"] = cb_map["disputed_amount"].abs()
    cb_map["chargeback_count"] = 1
    return cb_map[["source", "target", "edge_type",
                   "transaction_count", "total_amount",
                   "chargeback_count", "disputed_amount"]].copy()


def build_user_merchant_edges(txns: pd.DataFrame,
                              cb: pd.DataFrame) -> pd.DataFrame:
    """
    USER -[TRANSACTED_WITH]-> MERCHANT (aggregated per user-merchant pair)
    """
    txn_ts = pd.to_datetime(txns["timestamp_clean"], errors="coerce")

    base = txns[["user_id_normalized", "merchant_id_normalized",
                 "txn_id_normalized", "amount_numeric",
                 "chargeback_count", "total_disputed_amount"]].copy()
    base["ts"] = txn_ts

    agg = base.groupby(["user_id_normalized", "merchant_id_normalized"],
                       as_index=False).agg(
        transaction_count=("txn_id_normalized", "count"),
        total_amount=("amount_numeric", lambda x: x.abs().sum()),
        avg_amount=("amount_numeric", lambda x: x.abs().mean()),
        first_transaction_time=("ts", "min"),
        last_transaction_time=("ts", "max"),
        chargeback_count=("chargeback_count", "sum"),
        disputed_amount=("total_disputed_amount", "sum"),
    )
    agg["relationship_duration_days"] = (
        (agg["last_transaction_time"] - agg["first_transaction_time"])
        .dt.total_seconds() / 86400
    ).round(2)
    # txn frequency = txn_count / max(duration_days, 1)
    agg["transaction_frequency_per_day"] = (
        agg["transaction_count"] /
        agg["relationship_duration_days"].clip(lower=1)
    ).round(4)

    agg = agg.rename(columns={
        "user_id_normalized": "source",
        "merchant_id_normalized": "target",
    })
    agg["edge_type"] = "TRANSACTED_WITH"
    return agg


# ---------------------------------------------------------------------------
# 3. Combined edge CSV (standardised schema)
# ---------------------------------------------------------------------------

def build_all_edges(data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    txns = data["txns"]
    cb   = data["cb"]

    e_performed = build_performed_edges(txns)
    e_at_merch  = build_at_merchant_edges(txns)
    e_has_cb    = build_has_chargeback_edges(txns, cb)

    um_rels = build_user_merchant_edges(txns, cb)

    # Standardised edge list for graph_edges.csv
    um_std = um_rels[["source", "target", "edge_type",
                       "transaction_count", "total_amount",
                       "chargeback_count", "disputed_amount"]].copy()

    all_edges = pd.concat([e_performed, e_at_merch, e_has_cb, um_std],
                          axis=0, ignore_index=True, sort=False)
    return all_edges, um_rels


# ---------------------------------------------------------------------------
# 4. NetworkX Graph
# ---------------------------------------------------------------------------

def build_networkx_graph(nodes: pd.DataFrame,
                         um_rels: pd.DataFrame) -> nx.Graph:
    """
    Build an undirected bipartite USER↔MERCHANT graph.
    Used for connected-component cluster detection.
    Each edge is weighted by transaction_count.
    """
    G = nx.Graph()
    # Add user nodes
    user_nodes = nodes[nodes["node_type"] == "USER"]
    for _, row in user_nodes.iterrows():
        G.add_node(row["node_id"],
                   node_type="USER",
                   risk_score=row.get("risk_score", 0))
    # Add merchant nodes
    merch_nodes = nodes[nodes["node_type"] == "MERCHANT"]
    for _, row in merch_nodes.iterrows():
        G.add_node(row["node_id"],
                   node_type="MERCHANT",
                   risk_score=row.get("risk_score", 0))
    # Add edges
    for _, row in um_rels.iterrows():
        G.add_edge(row["source"], row["target"],
                   weight=row["transaction_count"],
                   chargeback_count=row["chargeback_count"],
                   disputed_amount=row["disputed_amount"],
                   total_amount=row["total_amount"])
    return G


# ---------------------------------------------------------------------------
# 5. Graph Metrics
# ---------------------------------------------------------------------------

def compute_graph_metrics(G: nx.Graph) -> dict[str, dict]:
    """
    Compute useful graph metrics for investigation.
    Only metrics with clear investigative value are retained.
    """
    degree_dict   = dict(G.degree())
    weighted_deg  = dict(G.degree(weight="weight"))
    deg_centrality = nx.degree_centrality(G)

    # Betweenness centrality: limit to top-500 nodes by degree for performance
    top_nodes = sorted(degree_dict, key=lambda n: degree_dict[n], reverse=True)[:500]
    sub = G.subgraph(top_nodes)
    btw = nx.betweenness_centrality(sub, weight="weight", normalized=True)

    return {
        "degree": degree_dict,
        "weighted_degree": weighted_deg,
        "degree_centrality": deg_centrality,
        "betweenness_centrality_top500": btw,
    }


# ---------------------------------------------------------------------------
# 6. Temporal Concentration Helper
# ---------------------------------------------------------------------------

def _temporal_concentration(txns: pd.DataFrame,
                             user_ids: set,
                             merchant_ids: set,
                             window_hours: int = 24) -> float:
    """
    Fraction of cluster transactions that fall within ANY 24-hour window.
    Uses a sliding-window scan.
    Returns a value in [0, 1].
    """
    mask = (txns["user_id_normalized"].isin(user_ids) &
            txns["merchant_id_normalized"].isin(merchant_ids))
    sub = txns.loc[mask, "timestamp_clean"].copy()
    if len(sub) < 2:
        return 0.0
    ts = pd.to_datetime(sub, errors="coerce").dropna().sort_values()
    if len(ts) < 2:
        return 0.0
    window = pd.Timedelta(hours=window_hours)
    max_in_window = 0
    ts_arr = ts.values
    n = len(ts_arr)
    j = 0
    for i in range(n):
        while j < n and (ts_arr[j] - ts_arr[i]) <= window.to_timedelta64():
            j += 1
        max_in_window = max(max_in_window, j - i)
    return round(max_in_window / n, 4)


# ---------------------------------------------------------------------------
# 7. Cluster Detection
# ---------------------------------------------------------------------------

RISK_LEVEL_TO_SCORE = {"LOW": 10, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 100}


def _score_norm(value: float, max_val: float) -> float:
    """Normalise a value to [0, 1] using a known maximum."""
    if max_val <= 0:
        return 0.0
    return min(1.0, value / max_val)


def score_cluster(component: set[str],
                  nodes: pd.DataFrame,
                  um_rels: pd.DataFrame,
                  txns: pd.DataFrame) -> Optional[dict]:
    """
    Score a single connected component as a potential investigation candidate.

    Cluster risk formula (documented):
      score = 100 × (
          0.25 × norm(max_member_risk, 100)       [ceiling risk]
        + 0.20 × norm(avg_member_risk, 100)       [average exposure]
        + 0.20 × chargeback_rate                  [chargeback concentration]
        + 0.15 × min(1, disputed_amount_ratio)    [financial exposure]
        + 0.10 × temporal_concentration           [burst detection]
        + 0.10 × relationship_concentration       [repeat relationships]
      )

    Returns None if the component fails the minimum evidence gate.
    """
    user_ids     = {n for n in component if n.startswith("USR")}
    merchant_ids = {n for n in component if n.startswith("MCH")}

    if not user_ids or not merchant_ids:
        return None  # singletons / no cross-entity relationship

    # --- Node risk scores ---
    user_scores = nodes.loc[
        nodes["node_id"].isin(user_ids) & (nodes["node_type"] == "USER"),
        "risk_score"
    ].dropna()
    merch_scores = nodes.loc[
        nodes["node_id"].isin(merchant_ids) & (nodes["node_type"] == "MERCHANT"),
        "risk_score"
    ].dropna()

    avg_user_risk   = float(user_scores.mean()) if len(user_scores) else 0.0
    max_user_risk   = float(user_scores.max())  if len(user_scores) else 0.0
    avg_merch_risk  = float(merch_scores.mean()) if len(merch_scores) else 0.0
    max_merch_risk  = float(merch_scores.max())  if len(merch_scores) else 0.0

    # --- Transaction stats ---
    pair_mask = (
        um_rels["source"].isin(user_ids) &
        um_rels["target"].isin(merchant_ids)
    )
    pairs = um_rels[pair_mask]
    total_txn_count = int(pairs["transaction_count"].sum())
    total_amount    = float(pairs["total_amount"].sum())
    total_cb        = int(pairs["chargeback_count"].sum())
    total_disputed  = float(pairs["disputed_amount"].sum())

    cluster_chargeback_rate = total_cb / total_txn_count if total_txn_count > 0 else 0.0
    disputed_ratio = total_disputed / total_amount if total_amount > 0 else 0.0

    # --- Temporal concentration ---
    temp_conc = _temporal_concentration(txns, user_ids, merchant_ids)

    # --- Relationship concentration (any pair with ≥ 3 repeated txns) ---
    max_pair_txns = int(pairs["transaction_count"].max()) if len(pairs) else 0
    rel_conc = _score_norm(max_pair_txns, 10)  # saturates at 10 repeat txns

    # --- Evidence gate: minimum 2 signals ---
    signals_present = []
    if avg_user_risk >= 15:
        signals_present.append("elevated_avg_user_risk")
    if max_user_risk >= 25:
        signals_present.append("elevated_max_user_risk")
    if avg_merch_risk >= 25:
        signals_present.append("elevated_avg_merchant_risk")
    if cluster_chargeback_rate >= 0.10:
        signals_present.append("high_cluster_chargeback_rate")
    if disputed_ratio >= 0.20:
        signals_present.append("high_disputed_amount_ratio")
    if temp_conc >= 0.50:
        signals_present.append("temporal_concentration")
    if max_pair_txns >= 3:
        signals_present.append("repeated_user_merchant_relationship")

    if len(signals_present) < 2:
        return None  # minimum evidence not met

    # --- Cluster score ---
    score = 100.0 * (
        0.25 * _score_norm(max(max_user_risk, max_merch_risk), 100)
      + 0.20 * _score_norm(max(avg_user_risk, avg_merch_risk), 100)
      + 0.20 * min(1.0, cluster_chargeback_rate)
      + 0.15 * min(1.0, disputed_ratio)
      + 0.10 * temp_conc
      + 0.10 * rel_conc
    )
    score = round(min(100.0, score), 4)

    # --- Risk level ---
    if score >= 70:
        risk_level = "HIGH"
    elif score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # --- Explanation ---
    signal_str = ", ".join(signals_present[:3])
    explanation = (
        f"Investigation candidate due to: {signal_str}. "
        f"Cluster involves {len(user_ids)} user(s) and {len(merchant_ids)} "
        f"merchant(s) with {total_txn_count} transaction(s), "
        f"chargeback rate {cluster_chargeback_rate:.1%}, "
        f"disputed amount ratio {disputed_ratio:.1%}."
    )

    return dict(
        n_users=len(user_ids),
        n_merchants=len(merchant_ids),
        n_transactions=total_txn_count,
        transaction_amount=round(total_amount, 2),
        chargeback_count=total_cb,
        disputed_amount=round(total_disputed, 2),
        average_user_risk=round(avg_user_risk, 4),
        average_merchant_risk=round(avg_merch_risk, 4),
        max_user_risk=round(max_user_risk, 4),
        max_merchant_risk=round(max_merch_risk, 4),
        cluster_chargeback_rate=round(cluster_chargeback_rate, 4),
        disputed_amount_ratio=round(disputed_ratio, 4),
        temporal_concentration=round(temp_conc, 4),
        relationship_concentration=round(rel_conc, 4),
        cluster_risk_score=score,
        risk_level=risk_level,
        top_signals="|".join(signals_present),
        explanation=explanation,
        _user_ids=user_ids,
        _merchant_ids=merchant_ids,
    )


def detect_clusters(G: nx.Graph,
                    nodes: pd.DataFrame,
                    um_rels: pd.DataFrame,
                    txns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run connected-component-based cluster detection.
    Returns (suspicious_clusters, cluster_members).
    """
    components = list(nx.connected_components(G))
    rows = []
    members = []

    cluster_num = 0
    for comp in sorted(components, key=lambda c: -len(c)):
        result = score_cluster(comp, nodes, um_rels, txns)
        if result is None:
            continue
        cluster_num += 1
        cid = f"CLU{cluster_num:05d}"

        row = {k: v for k, v in result.items()
               if not k.startswith("_")}
        row["cluster_id"] = cid
        rows.append(row)

        # Member records
        for uid in result["_user_ids"]:
            members.append({"cluster_id": cid, "node_id": uid,
                            "node_type": "USER"})
        for mid in result["_merchant_ids"]:
            members.append({"cluster_id": cid, "node_id": mid,
                            "node_type": "MERCHANT"})

    if not rows:
        clusters_df = pd.DataFrame(columns=[
            "cluster_id", "n_users", "n_merchants", "n_transactions",
            "transaction_amount", "chargeback_count", "disputed_amount",
            "average_user_risk", "average_merchant_risk",
            "max_user_risk", "max_merchant_risk",
            "cluster_chargeback_rate", "disputed_amount_ratio",
            "temporal_concentration", "relationship_concentration",
            "cluster_risk_score", "risk_level", "top_signals", "explanation",
        ])
        members_df = pd.DataFrame(columns=["cluster_id", "node_id", "node_type"])
    else:
        clusters_df = pd.DataFrame(rows)
        # Reorder columns
        col_order = [
            "cluster_id", "n_users", "n_merchants", "n_transactions",
            "transaction_amount", "chargeback_count", "disputed_amount",
            "average_user_risk", "average_merchant_risk",
            "max_user_risk", "max_merchant_risk",
            "cluster_chargeback_rate", "disputed_amount_ratio",
            "temporal_concentration", "relationship_concentration",
            "cluster_risk_score", "risk_level", "top_signals", "explanation",
        ]
        clusters_df = clusters_df[col_order].sort_values(
            "cluster_risk_score", ascending=False
        ).reset_index(drop=True)
        members_df = pd.DataFrame(members)

    return clusters_df, members_df


# ---------------------------------------------------------------------------
# 8. Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> dict:
    """Run the full M7 graph analysis pipeline. Returns a summary dict."""
    print("[M7] Loading inputs …")
    data = load_inputs()

    print("[M7] Building nodes …")
    nodes = build_all_nodes(data)

    print("[M7] Building edges …")
    all_edges, um_rels = build_all_edges(data)

    print("[M7] Building NetworkX graph …")
    G = build_networkx_graph(nodes, um_rels)

    print("[M7] Computing graph metrics …")
    metrics = compute_graph_metrics(G)

    # Attach degree to nodes table for reference
    nodes["degree"] = nodes["node_id"].map(metrics["degree"]).fillna(0).astype(int)
    nodes["weighted_degree"] = nodes["node_id"].map(
        metrics["weighted_degree"]).fillna(0)
    nodes["degree_centrality"] = nodes["node_id"].map(
        metrics["degree_centrality"]).fillna(0)

    print("[M7] Detecting suspicious clusters …")
    clusters, members = detect_clusters(
        G, nodes, um_rels, data["txns"]
    )

    # -----------------------------------------------------------------------
    # Save outputs
    # -----------------------------------------------------------------------
    print("[M7] Saving outputs …")

    # graph_nodes.csv — all node types
    nodes_out = nodes.copy()
    nodes_out.to_csv(GRAPH_DIR / "graph_nodes.csv", index=False)

    # graph_edges.csv — all edge types (standardised schema)
    all_edges.to_csv(GRAPH_DIR / "graph_edges.csv", index=False)

    # user_merchant_relationships.csv — enriched USER↔MERCHANT pairs
    um_rels.to_csv(GRAPH_DIR / "user_merchant_relationships.csv", index=False)

    # suspicious_clusters.csv
    clusters.to_csv(GRAPH_DIR / "suspicious_clusters.csv", index=False)

    # cluster_members.csv
    members.to_csv(GRAPH_DIR / "cluster_members.csv", index=False)

    summary = dict(
        n_user_nodes=int((nodes["node_type"] == "USER").sum()),
        n_merchant_nodes=int((nodes["node_type"] == "MERCHANT").sum()),
        n_transaction_nodes=int((nodes["node_type"] == "TRANSACTION").sum()),
        n_chargeback_nodes=int((nodes["node_type"] == "CHARGEBACK").sum()),
        total_nodes=len(nodes),
        n_edges_performed=len(all_edges[all_edges["edge_type"] == "PERFORMED"]),
        n_edges_at_merchant=len(all_edges[all_edges["edge_type"] == "AT_MERCHANT"]),
        n_edges_has_chargeback=len(all_edges[all_edges["edge_type"] == "HAS_CHARGEBACK"]),
        n_edges_transacted_with=len(all_edges[all_edges["edge_type"] == "TRANSACTED_WITH"]),
        total_edges=len(all_edges),
        n_user_merchant_pairs=len(um_rels),
        n_graph_nodes_um=G.number_of_nodes(),
        n_graph_edges_um=G.number_of_edges(),
        n_connected_components=nx.number_connected_components(G),
        n_clusters_detected=len(clusters),
        n_cluster_members=len(members),
    )
    if len(clusters) > 0:
        summary["cluster_risk_score_max"]    = float(clusters["cluster_risk_score"].max())
        summary["cluster_risk_score_mean"]   = float(clusters["cluster_risk_score"].mean())
        summary["cluster_risk_distribution"] = clusters["risk_level"].value_counts().to_dict()

    print("[M7] Pipeline complete.")
    return summary


if __name__ == "__main__":
    summary = run_pipeline()
    print("\n=== M7 Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
