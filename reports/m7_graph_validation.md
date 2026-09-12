# M7 Graph Analysis — Validation Report

**Date:** 2026-09-13

---

## A. Graph Construction Validation

### Node Reconciliation

| Node Type   | Expected (Source) | In Graph | Match |
|-------------|-------------------|----------|-------|
| USER        | 17,878 (M6)       | 17,878   | ✅    |
| MERCHANT    | 8,051 (M6)        | 8,051    | ✅    |
| TRANSACTION | 20,000 (M3)       | 20,000   | ✅    |
| CHARGEBACK  | 2,800 (M3)        | 2,800    | ✅    |
| **TOTAL**   | **48,729**        | **48,729** | ✅  |

No duplicate `node_id` values. No null `node_id` values.

### Edge Reconciliation

| Edge Type       | Expected | In File | Match |
|-----------------|----------|---------|-------|
| PERFORMED       | 20,000   | 20,000  | ✅    |
| AT_MERCHANT     | 20,000   | 20,000  | ✅    |
| HAS_CHARGEBACK  | 2,800    | 2,800   | ✅    |
| TRANSACTED_WITH | 20,000   | 20,000  | ✅    |
| **TOTAL**       | **62,800** | **62,800** | ✅ |

No duplicate (source, target, edge_type) triplets. All source/target IDs verified
against their respective node lists.

---

## B. No Fabricated Relationships

| Check | Result |
|-------|--------|
| All USER node_ids exist in `finguard_transactions.user_id_normalized` | ✅ |
| All MERCHANT node_ids exist in `finguard_transactions.merchant_id_normalized` | ✅ |
| All TRANSACTION node_ids exist in `finguard_transactions.txn_id_normalized` | ✅ |
| All CHARGEBACK node_ids exist in `chargebacks_clean.complaint_id_normalized` | ✅ |
| No fuzzy matching used | ✅ |
| No approximate IDs created | ✅ |

---

## C. NetworkX Graph (USER↔MERCHANT Bipartite)

| Metric | Value |
|--------|-------|
| Graph nodes | 25,929 |
| Graph edges | 20,000 |
| Connected components | 5,929 |
| Largest component size | to be explored in M8 dashboard |
| Betweenness computed on top-N nodes | Top 500 |

---

## D. User–Merchant Relationship Table

| Metric | Value |
|--------|-------|
| Total pairs | 20,000 |
| Unique users | 17,878 |
| Unique merchants | 8,051 |
| Max transactions per pair | 1 (all users visit each merchant at most once in this dataset) |
| Pairs with at least 1 chargeback | 2,451 |
| Pairs with ≥ 3 transactions | 0 (dataset characteristic, not an error) |

> **Dataset note**: In this 20,000-transaction dataset every (user, merchant) pair
> has exactly 1 transaction. The `repeated_user_merchant_relationship` signal therefore
> never fires. This is a confirmed data characteristic documented here, not an
> engine defect.

---

## E. Cluster Detection Results

| Metric | Value |
|--------|-------|
| Components evaluated | 5,929 |
| Clusters passing minimum-evidence gate (≥ 2 signals) | **655** |
| Cluster members (users + merchants) | 2,503 |
| Cluster risk score — minimum | 8.10 |
| Cluster risk score — maximum | 81.00 |
| Cluster risk score — mean | 26.82 |
| NaN scores | 0 |
| Inf scores | 0 |
| Scores outside [0, 100] | 0 |

### Risk Level Distribution

| Risk Level | Count | % of Clusters |
|------------|-------|---------------|
| HIGH       | 1     | 0.15 %        |
| MEDIUM     | 46    | 7.02 %        |
| LOW        | 608   | 92.8 %        |

---

## F. Cluster Integrity

| Check | Result |
|-------|--------|
| Every cluster has ≥ 1 USER member | ✅ |
| Every cluster has ≥ 1 MERCHANT member | ✅ |
| Every member references a valid cluster_id | ✅ |
| Every cluster_id has at least one member row | ✅ |
| No orphan members | ✅ |

---

## G. Minimum Evidence Rule

All 655 clusters satisfy ≥ 2 signals from the evidence gate. Verified by:
- `TestMinimumEvidenceRule::test_all_clusters_have_at_least_two_signals` ✅
- Manual inspection of `top_signals` column (pipe-separated, always ≥ 2 tokens)

---

## H. Score Formula Validation

The formula weights sum to exactly **1.00**:

| Component | Weight |
|-----------|--------|
| `norm(max_member_risk, 100)` | 0.25 |
| `norm(avg_member_risk, 100)` | 0.20 |
| `min(1, chargeback_rate)` | 0.20 |
| `min(1, disputed_amount_ratio)` | 0.15 |
| `temporal_concentration` | 0.10 |
| `relationship_concentration` | 0.10 |
| **Total** | **1.00** |

Maximum possible raw value = 1.00 × 100 = 100. Verified no cluster exceeds 100.

---

## I. Temporal Concentration Validation

- Algorithm: two-pointer sliding window on sorted `timestamp_clean` values
- Window: 24 hours
- Result is in [0, 1] by construction (ratio of max_window_count to total_count)
- No NaN or Inf produced (guarded by `len(ts) < 2` early exit)

---

## J. Chargeback Concentration — Numerator/Denominator Preservation

`suspicious_clusters.csv` always records:
- `chargeback_count` — raw numerator
- `n_transactions` — raw denominator  
- `cluster_chargeback_rate` — derived rate

A cluster with 2 chargebacks / 2 transactions and a cluster with
2 chargebacks / 200 transactions will have the same rate but different
raw counts, visible to the analyst.

---

## K. Determinism

Running cluster detection twice on identical inputs produces bit-for-bit
identical `cluster_risk_score` values.

**Test:** `TestDeterminism::test_deterministic_clusters` ✅

---

## L. Singleton Handling

- Isolated nodes (no cross-entity relationship) are stored in `graph_nodes.csv`
  for completeness.
- They are excluded from `suspicious_clusters.csv` (the `score_cluster()` function
  returns `None` for components with no users or no merchants).
- No singleton is labeled an investigation candidate.

---

## M. Pytest Results

**36 / 36 tests passed** in 120.49 s

| Test Class | Tests | Status |
|------------|-------|--------|
| `TestNodeUniqueness` | 4 | ✅ PASS |
| `TestEdgeUniqueness` | 5 | ✅ PASS |
| `TestValidNodeReferences` | 4 | ✅ PASS |
| `TestReconciliation` | 4 | ✅ PASS |
| `TestNoFabricatedIDs` | 3 | ✅ PASS |
| `TestClusterScoreBounds` | 5 | ✅ PASS |
| `TestClusterMemberIntegrity` | 3 | ✅ PASS |
| `TestMinimumEvidenceRule` | 2 | ✅ PASS |
| `TestSingletonHandling` | 2 | ✅ PASS |
| `TestDeterminism` | 1 | ✅ PASS |
| `TestGraphMetrics` | 3 | ✅ PASS |

1 warning (DtypeWarning on mixed-type columns in graph_nodes.csv — cosmetic only,
does not affect correctness).

---

## N. M7 Acceptance Criteria Checklist

| Criterion | Status |
|-----------|--------|
| Graph constructed | ✅ |
| Nodes validated | ✅ |
| Edges validated | ✅ |
| User↔merchant relationships built | ✅ |
| Chargeback relationships represented | ✅ |
| No fabricated relationships | ✅ |
| Cluster detection implemented | ✅ |
| Minimum evidence rule implemented | ✅ |
| Temporal concentration implemented | ✅ |
| Chargeback concentration implemented | ✅ |
| Cluster scoring explainable | ✅ |
| Cluster score 0–100 | ✅ |
| Cluster explanations generated | ✅ |
| Reconciliation completed | ✅ |
| Tests pass (36/36) | ✅ |
| Methodology documented | ✅ |
| Validation documented | ✅ |
| Dashboard NOT started | ✅ |
| M8 NOT started | ✅ |
