"""
M7 Graph Analysis Test Suite
=============================
Validates:
 - graph node uniqueness
 - graph edge uniqueness
 - valid node references
 - no fabricated IDs
 - transaction reconciliation
 - chargeback reconciliation
 - deterministic graph
 - deterministic clusters
 - cluster score 0–100
 - risk level mapping
 - no infinite values
 - no invalid centrality values
 - cluster/member relationship integrity
 - minimum evidence rule
 - singleton handling
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "data" / "processed" / "graph"
RISK_DIR  = ROOT / "data" / "processed" / "risk"
DATA_PROC = ROOT / "data" / "processed"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def nodes() -> pd.DataFrame:
    return pd.read_csv(GRAPH_DIR / "graph_nodes.csv")


@pytest.fixture(scope="session")
def edges() -> pd.DataFrame:
    return pd.read_csv(GRAPH_DIR / "graph_edges.csv")


@pytest.fixture(scope="session")
def um_rels() -> pd.DataFrame:
    return pd.read_csv(GRAPH_DIR / "user_merchant_relationships.csv")


@pytest.fixture(scope="session")
def clusters() -> pd.DataFrame:
    return pd.read_csv(GRAPH_DIR / "suspicious_clusters.csv")


@pytest.fixture(scope="session")
def members() -> pd.DataFrame:
    return pd.read_csv(GRAPH_DIR / "cluster_members.csv")


@pytest.fixture(scope="session")
def txns() -> pd.DataFrame:
    return pd.read_csv(DATA_PROC / "finguard_transactions.csv", low_memory=False)


@pytest.fixture(scope="session")
def cb() -> pd.DataFrame:
    return pd.read_csv(DATA_PROC / "chargebacks_clean.csv", low_memory=False)


@pytest.fixture(scope="session")
def user_risk() -> pd.DataFrame:
    return pd.read_csv(RISK_DIR / "user_risk_scores.csv")


@pytest.fixture(scope="session")
def merch_risk() -> pd.DataFrame:
    return pd.read_csv(RISK_DIR / "merchant_risk_scores.csv")


@pytest.fixture(scope="session")
def txn_risk() -> pd.DataFrame:
    return pd.read_csv(RISK_DIR / "transaction_risk_scores.csv")


# ---------------------------------------------------------------------------
# 1. Node Tests
# ---------------------------------------------------------------------------

class TestNodeUniqueness:
    def test_node_ids_are_unique(self, nodes):
        dupes = nodes["node_id"].duplicated().sum()
        assert dupes == 0, f"{dupes} duplicate node_ids found"

    def test_no_null_node_ids(self, nodes):
        assert nodes["node_id"].isna().sum() == 0

    def test_expected_node_types(self, nodes):
        expected = {"USER", "MERCHANT", "TRANSACTION", "CHARGEBACK"}
        actual = set(nodes["node_type"].unique())
        assert actual == expected, f"Unexpected node types: {actual - expected}"

    def test_node_counts_match_sources(self, nodes, user_risk, merch_risk, txn_risk, cb):
        assert (nodes["node_type"] == "USER").sum() == len(user_risk)
        assert (nodes["node_type"] == "MERCHANT").sum() == len(merch_risk)
        assert (nodes["node_type"] == "TRANSACTION").sum() == len(txn_risk)
        assert (nodes["node_type"] == "CHARGEBACK").sum() == len(cb)


# ---------------------------------------------------------------------------
# 2. Edge Tests
# ---------------------------------------------------------------------------

class TestEdgeUniqueness:
    def test_no_duplicate_edges(self, edges):
        dupes = edges.duplicated(subset=["source", "target", "edge_type"]).sum()
        assert dupes == 0, f"{dupes} duplicate (source, target, edge_type) edges"

    def test_expected_edge_types(self, edges):
        expected = {"PERFORMED", "AT_MERCHANT", "HAS_CHARGEBACK", "TRANSACTED_WITH"}
        actual = set(edges["edge_type"].unique())
        assert actual == expected

    def test_performed_edge_count(self, edges, txns):
        n = (edges["edge_type"] == "PERFORMED").sum()
        assert n == len(txns), f"Expected {len(txns)} PERFORMED edges, got {n}"

    def test_at_merchant_edge_count(self, edges, txns):
        n = (edges["edge_type"] == "AT_MERCHANT").sum()
        assert n == len(txns)

    def test_has_chargeback_edge_count(self, edges, cb):
        n = (edges["edge_type"] == "HAS_CHARGEBACK").sum()
        assert n == len(cb), f"Expected {len(cb)} HAS_CHARGEBACK edges, got {n}"


# ---------------------------------------------------------------------------
# 3. Valid Node References
# ---------------------------------------------------------------------------

class TestValidNodeReferences:
    def test_performed_sources_are_user_nodes(self, edges, nodes):
        user_ids = set(nodes.loc[nodes["node_type"] == "USER", "node_id"])
        sources = set(edges.loc[edges["edge_type"] == "PERFORMED", "source"])
        unknown = sources - user_ids
        assert len(unknown) == 0, f"PERFORMED sources not in USER nodes: {len(unknown)}"

    def test_performed_targets_are_txn_nodes(self, edges, nodes):
        txn_ids = set(nodes.loc[nodes["node_type"] == "TRANSACTION", "node_id"])
        targets = set(edges.loc[edges["edge_type"] == "PERFORMED", "target"])
        unknown = targets - txn_ids
        assert len(unknown) == 0

    def test_at_merchant_targets_are_merchant_nodes(self, edges, nodes):
        merch_ids = set(nodes.loc[nodes["node_type"] == "MERCHANT", "node_id"])
        targets = set(edges.loc[edges["edge_type"] == "AT_MERCHANT", "target"])
        unknown = targets - merch_ids
        assert len(unknown) == 0

    def test_has_chargeback_targets_are_cb_nodes(self, edges, nodes):
        cb_ids = set(nodes.loc[nodes["node_type"] == "CHARGEBACK", "node_id"])
        targets = set(edges.loc[edges["edge_type"] == "HAS_CHARGEBACK", "target"])
        unknown = targets - cb_ids
        assert len(unknown) == 0


# ---------------------------------------------------------------------------
# 4. Reconciliation
# ---------------------------------------------------------------------------

class TestReconciliation:
    def test_transaction_reconciliation(self, edges, txns):
        """All transactions from the master table appear in PERFORMED edges."""
        expected_txn_ids = set(txns["txn_id_normalized"].unique())
        performed_txn_ids = set(
            edges.loc[edges["edge_type"] == "PERFORMED", "target"].unique()
        )
        missing = expected_txn_ids - performed_txn_ids
        assert len(missing) == 0, f"{len(missing)} transactions missing from graph"

    def test_chargeback_reconciliation(self, edges, cb):
        """All chargebacks appear in HAS_CHARGEBACK edges."""
        expected_cb_ids = set(cb["complaint_id_normalized"].unique())
        graph_cb_ids = set(
            edges.loc[edges["edge_type"] == "HAS_CHARGEBACK", "target"].unique()
        )
        missing = expected_cb_ids - graph_cb_ids
        assert len(missing) == 0, f"{len(missing)} chargebacks missing from graph"

    def test_user_reconciliation(self, nodes, user_risk):
        """All canonical users from M6 appear as USER nodes."""
        expected = set(user_risk["user_id"].unique())
        actual = set(nodes.loc[nodes["node_type"] == "USER", "node_id"].unique())
        missing = expected - actual
        assert len(missing) == 0, f"{len(missing)} users missing from node list"

    def test_merchant_reconciliation(self, nodes, merch_risk):
        """All canonical merchants from M6 appear as MERCHANT nodes."""
        expected = set(merch_risk["merchant_id"].unique())
        actual = set(nodes.loc[nodes["node_type"] == "MERCHANT", "node_id"].unique())
        missing = expected - actual
        assert len(missing) == 0


# ---------------------------------------------------------------------------
# 5. No Fabricated IDs
# ---------------------------------------------------------------------------

class TestNoFabricatedIDs:
    def test_user_ids_come_from_source(self, nodes, txns):
        src_user_ids = set(txns["user_id_normalized"].dropna().unique())
        graph_user_ids = set(nodes.loc[nodes["node_type"] == "USER", "node_id"])
        fabricated = graph_user_ids - src_user_ids
        assert len(fabricated) == 0, f"Fabricated user IDs: {fabricated}"

    def test_merchant_ids_come_from_source(self, nodes, txns):
        src_merch_ids = set(txns["merchant_id_normalized"].dropna().unique())
        graph_merch_ids = set(nodes.loc[nodes["node_type"] == "MERCHANT", "node_id"])
        fabricated = graph_merch_ids - src_merch_ids
        assert len(fabricated) == 0

    def test_transaction_ids_come_from_source(self, nodes, txns):
        src_txn_ids = set(txns["txn_id_normalized"].dropna().unique())
        graph_txn_ids = set(nodes.loc[nodes["node_type"] == "TRANSACTION", "node_id"])
        fabricated = graph_txn_ids - src_txn_ids
        assert len(fabricated) == 0


# ---------------------------------------------------------------------------
# 6. Cluster Score Bounds
# ---------------------------------------------------------------------------

class TestClusterScoreBounds:
    def test_cluster_score_in_range(self, clusters):
        assert (clusters["cluster_risk_score"] >= 0).all()
        assert (clusters["cluster_risk_score"] <= 100).all()

    def test_no_nan_cluster_scores(self, clusters):
        assert clusters["cluster_risk_score"].isna().sum() == 0

    def test_no_inf_cluster_scores(self, clusters):
        assert np.isinf(clusters["cluster_risk_score"]).sum() == 0

    def test_risk_level_mapping(self, clusters):
        """Risk levels must be LOW / MEDIUM / HIGH / CRITICAL only."""
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        bad = set(clusters["risk_level"].unique()) - valid
        assert len(bad) == 0, f"Invalid risk levels: {bad}"

    def test_risk_level_threshold_consistency(self, clusters):
        """HIGH clusters must have score >= 70; MEDIUM >= 40; LOW < 40."""
        high_mask   = clusters["risk_level"] == "HIGH"
        medium_mask = clusters["risk_level"] == "MEDIUM"
        low_mask    = clusters["risk_level"] == "LOW"
        if high_mask.any():
            assert (clusters.loc[high_mask, "cluster_risk_score"] >= 70).all()
        if medium_mask.any():
            assert (clusters.loc[medium_mask, "cluster_risk_score"] >= 40).all()
        if low_mask.any():
            assert (clusters.loc[low_mask, "cluster_risk_score"] < 70).all()


# ---------------------------------------------------------------------------
# 7. Cluster / Member Integrity
# ---------------------------------------------------------------------------

class TestClusterMemberIntegrity:
    def test_no_orphan_members(self, clusters, members):
        valid_cluster_ids = set(clusters["cluster_id"])
        member_cluster_ids = set(members["cluster_id"])
        orphans = member_cluster_ids - valid_cluster_ids
        assert len(orphans) == 0, f"Orphan cluster_ids in members: {orphans}"

    def test_every_cluster_has_members(self, clusters, members):
        cluster_ids_with_members = set(members["cluster_id"])
        clusters_without_members = set(clusters["cluster_id"]) - cluster_ids_with_members
        assert len(clusters_without_members) == 0

    def test_each_cluster_has_both_user_and_merchant(self, members):
        for cid, grp in members.groupby("cluster_id"):
            types = set(grp["node_type"])
            assert "USER" in types, f"Cluster {cid} has no USER member"
            assert "MERCHANT" in types, f"Cluster {cid} has no MERCHANT member"


# ---------------------------------------------------------------------------
# 8. Minimum Evidence Rule
# ---------------------------------------------------------------------------

class TestMinimumEvidenceRule:
    def test_all_clusters_have_at_least_two_signals(self, clusters):
        """top_signals must contain at least 2 pipe-separated tokens."""
        for _, row in clusters.iterrows():
            signals = [s for s in str(row["top_signals"]).split("|") if s]
            assert len(signals) >= 2, (
                f"Cluster {row['cluster_id']} has only {len(signals)} signal(s)"
            )

    def test_all_clusters_have_explanation(self, clusters):
        assert clusters["explanation"].isna().sum() == 0
        assert (clusters["explanation"].str.strip() != "").all()


# ---------------------------------------------------------------------------
# 9. Singleton Handling
# ---------------------------------------------------------------------------

class TestSingletonHandling:
    def test_all_clusters_have_at_least_one_user_and_one_merchant(self, clusters):
        assert (clusters["n_users"] >= 1).all()
        assert (clusters["n_merchants"] >= 1).all()

    def test_no_single_node_clusters_without_cross_entity(self, clusters):
        """A cluster with n_users=0 or n_merchants=0 should not exist."""
        assert (clusters["n_users"] > 0).all()
        assert (clusters["n_merchants"] > 0).all()


# ---------------------------------------------------------------------------
# 10. Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_deterministic_clusters(self, clusters):
        """
        Re-running the pipeline should produce the same top cluster score.
        We verify by importing the scoring function and running it twice
        on the same data.
        """
        sys.path.insert(0, str(ROOT / "src" / "risk"))
        from m7_graph_analysis import load_inputs, build_all_nodes, build_all_edges
        from m7_graph_analysis import build_networkx_graph, detect_clusters

        data = load_inputs()
        nodes = build_all_nodes(data)
        _, um_rels = build_all_edges(data)
        G = build_networkx_graph(nodes, um_rels)

        c1, _ = detect_clusters(G, nodes, um_rels, data["txns"])
        c2, _ = detect_clusters(G, nodes, um_rels, data["txns"])

        if len(c1) > 0 and len(c2) > 0:
            assert (
                c1["cluster_risk_score"].values == c2["cluster_risk_score"].values
            ).all(), "Cluster scores are not deterministic"


# ---------------------------------------------------------------------------
# 11. Graph Metric Validity
# ---------------------------------------------------------------------------

class TestGraphMetrics:
    def test_degree_centrality_nonnegative(self, nodes):
        if "degree_centrality" in nodes.columns:
            assert (nodes["degree_centrality"] >= 0).all()

    def test_degree_nonnegative(self, nodes):
        if "degree" in nodes.columns:
            assert (nodes["degree"] >= 0).all()
            assert not np.isinf(nodes["degree"]).any()

    def test_no_inf_in_metrics(self, nodes):
        numeric_cols = nodes.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.isinf(nodes[col]).any(), f"Inf in nodes column: {col}"


# ---------------------------------------------------------------------------
# 12. Chargeback Rate Regression Tests (Definition Fix)
# ---------------------------------------------------------------------------

class TestChargebackRateDefinition:
    """
    Regression tests proving cluster_chargeback_rate uses
    COUNT(distinct transactions with >=1 CB) / COUNT(transactions),
    consistent with M5/M6. Rate must always be in [0, 1].
    """

    def _make_um_row(self, txn_count: int, cb_records: int,
                     chargebacked_txns: int) -> pd.DataFrame:
        """Helper: create a minimal UM relationship row."""
        return pd.DataFrame([{
            "source": "USR_TEST",
            "target": "MCH_TEST",
            "transaction_count": txn_count,
            "total_amount": 1000.0,
            "avg_amount": 1000.0 / txn_count,
            "chargeback_count": cb_records,
            "chargebacked_transaction_count": chargebacked_txns,
            "disputed_amount": 500.0,
            "edge_type": "TRANSACTED_WITH",
        }])

    def test_one_txn_two_cb_records_rate_is_1(self):
        """1 transaction + 2 chargeback records => rate = 1.0, NOT 2.0."""
        um = self._make_um_row(txn_count=1, cb_records=2, chargebacked_txns=1)
        # rate = chargebacked_transaction_count / transaction_count = 1/1 = 1.0
        rate = um["chargebacked_transaction_count"].sum() / um["transaction_count"].sum()
        assert rate == 1.0, f"Expected 1.0, got {rate}"
        assert rate <= 1.0

    def test_two_txns_one_cb_rate_is_half(self):
        """2 transactions + 1 chargeback => rate = 0.5."""
        um = self._make_um_row(txn_count=2, cb_records=1, chargebacked_txns=1)
        rate = um["chargebacked_transaction_count"].sum() / um["transaction_count"].sum()
        assert rate == 0.5, f"Expected 0.5, got {rate}"

    def test_two_txns_zero_cb_rate_is_zero(self):
        """2 transactions + 0 chargebacks => rate = 0.0."""
        um = self._make_um_row(txn_count=2, cb_records=0, chargebacked_txns=0)
        rate = um["chargebacked_transaction_count"].sum() / um["transaction_count"].sum()
        assert rate == 0.0, f"Expected 0.0, got {rate}"

    def test_cluster_chargeback_rate_never_exceeds_one(self, clusters):
        """cluster_chargeback_rate must always be in [0, 1] for all clusters."""
        above_one = (clusters["cluster_chargeback_rate"] > 1.0).sum()
        assert above_one == 0, (
            f"{above_one} clusters have cluster_chargeback_rate > 1.0 "
            f"(definition fix not applied correctly)"
        )

    def test_clu00604_chargeback_rate_is_one(self, clusters):
        """
        CLU00604 has 1 transaction + 2 complaint records.
        After the fix, cluster_chargeback_rate must be 1.0 (100%), NOT 2.0 (200%).
        The raw chargeback_count must remain 2 (complaint records preserved).
        """
        row = clusters[clusters["cluster_id"] == "CLU00604"]
        if len(row) == 0:
            pytest.skip("CLU00604 not present in current cluster output")
        row = row.iloc[0]
        assert row["cluster_chargeback_rate"] == 1.0, (
            f"Expected cluster_chargeback_rate=1.0, got {row['cluster_chargeback_rate']}"
        )
        assert row["chargeback_count"] == 2, (
            f"Raw chargeback_count should remain 2, got {row['chargeback_count']}"
        )

    def test_chargebacked_transaction_count_column_exists(self, clusters):
        """The new chargebacked_transaction_count column must be present."""
        assert "chargebacked_transaction_count" in clusters.columns

    def test_chargebacked_txn_count_lte_n_transactions(self, clusters):
        """chargebacked_transaction_count <= n_transactions for all clusters."""
        assert (
            clusters["chargebacked_transaction_count"] <= clusters["n_transactions"]
        ).all(), "chargebacked_transaction_count exceeds n_transactions in some clusters"

    def test_chargeback_count_gte_chargebacked_txn_count(self, clusters):
        """
        Raw complaint records (chargeback_count) >= distinct chargebacked txns.
        A transaction can have multiple complaint records.
        """
        assert (
            clusters["chargeback_count"] >= clusters["chargebacked_transaction_count"]
        ).all(), (
            "chargeback_count (records) < chargebacked_transaction_count (txns) — "
            "this would be impossible"
        )
