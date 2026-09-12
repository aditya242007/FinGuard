# M7 Graph Analysis Methodology

## 1. Objective

M7 builds a **graph-based investigation layer** over FinGuard transaction data.
The goal is to surface:

- Suspicious transaction clusters
- Highly connected users and merchants
- Repeated user↔merchant relationships
- Concentrated chargeback relationships
- Temporal transaction bursts
- Networks containing multiple elevated-risk signals

> **IMPORTANT**: This tool is an investigation aid. It identifies behavioural
> patterns and investigation candidates. It does NOT confirm fraud, criminal
> coordination, or identity linkage beyond the dataset's own IDs.

---

## 2. Node Model

| Node Type   | ID Column                | Count  | Key Attributes |
|-------------|--------------------------|--------|----------------|
| USER        | `user_id_normalized`     | 17,878 | risk_score, risk_level, transaction_count, chargeback_rate |
| MERCHANT    | `merchant_id_normalized` | 8,051  | risk_score, chargeback_rate, disputed_amount_ratio |
| TRANSACTION | `txn_id_normalized`      | 20,000 | transaction_time_risk_score, retrospective_risk_score |
| CHARGEBACK  | `complaint_id_normalized`| 2,800  | disputed_amount, severity, resolution_status |

Risk scores are sourced directly from M6 outputs. No re-computation is performed.

---

## 3. Edge Model

| Edge Type        | Source      | Target      | Count  | Notes |
|------------------|-------------|-------------|--------|-------|
| PERFORMED        | USER        | TRANSACTION | 20,000 | One edge per transaction |
| AT_MERCHANT      | TRANSACTION | MERCHANT    | 20,000 | One edge per transaction |
| HAS_CHARGEBACK   | TRANSACTION | CHARGEBACK  | 2,800  | One edge per complaint |
| TRANSACTED_WITH  | USER        | MERCHANT    | 20,000 | Aggregated per pair |

### No Fabricated Edges
Edges are only created when both source and target IDs exist in the M3-normalized
dataset. No fuzzy matching, guessed identities, or approximate IDs are used.

---

## 4. Relationship Aggregation (USER↔MERCHANT)

The `user_merchant_relationships.csv` file aggregates per unique (user_id, merchant_id)
pair using actual transaction records:

| Column | Computation |
|--------|-------------|
| `transaction_count` | COUNT of transactions between the pair |
| `total_amount` | SUM of `abs(amount)` |
| `avg_amount` | MEAN of `abs(amount)` |
| `first_transaction_time` | MIN timestamp |
| `last_transaction_time` | MAX timestamp |
| `chargeback_count` | SUM of complaint records from M3 join (raw record count; can exceed `transaction_count` when one transaction has multiple complaint records — **preserved for completeness, not used as rate numerator**) |
| `chargebacked_transaction_count` | COUNT of distinct transactions with `has_chargeback = True` (binary flag from M3; always ≤ `transaction_count` — **used as the rate numerator, consistent with M5/M6 `chargeback_transaction_count`**) |
| `disputed_amount` | SUM of total_disputed_amount |
| `relationship_duration_days` | `(last - first).total_seconds() / 86400` |
| `transaction_frequency_per_day` | `txn_count / max(duration_days, 1)` |

---

## 5. Graph Construction

The primary investigation graph is a **bipartite USER↔MERCHANT undirected graph**
built with NetworkX 3.3:

- Each USER and MERCHANT becomes a node.
- Each unique user↔merchant pair becomes an edge, weighted by `transaction_count`.
- Only USER and MERCHANT nodes appear in this graph (TRANSACTION and CHARGEBACK
  nodes are stored in `graph_nodes.csv` but not added to the NetworkX graph, which
  would create a tripartite structure that complicates component detection).

This produces:
- **25,929** graph nodes (17,878 users + 8,051 merchants)
- **20,000** edges
- **5,929** connected components

---

## 6. Graph Metrics

The following metrics are computed and retained for investigative value:

| Metric | Scope | Purpose |
|--------|-------|---------|
| `degree` | All nodes | How many distinct counterparties |
| `weighted_degree` | All nodes | Transaction-count-weighted connectivity |
| `degree_centrality` | All nodes | Normalised degree |
| `betweenness_centrality` | Top-500 nodes by degree | Bridge nodes across clusters |

**Note on betweenness**: computed only on the top-500 highest-degree nodes for
performance. The full graph (25k+ nodes) betweenness computation would take
minutes with marginal investigative benefit on a 20k-transaction dataset.

---

## 7. Cluster Detection Methodology

### Algorithm
Connected components of the USER↔MERCHANT bipartite graph are extracted using
`networkx.connected_components`. Each component is treated as a candidate cluster.

### Minimum Evidence Gate
A component is elevated to an **investigation candidate** only if it satisfies
**at least 2** of the following 7 signals:

| Signal | Condition | Rationale |
|--------|-----------|-----------|
| `elevated_avg_user_risk` | avg_user_risk ≥ 15 | Group has broadly elevated users |
| `elevated_max_user_risk` | max_user_risk ≥ 25 | At least one elevated-risk user |
| `elevated_avg_merchant_risk` | avg_merchant_risk ≥ 25 | MEDIUM+ merchant |
| `high_cluster_chargeback_rate` | cluster_chargeback_rate ≥ 10% | Above-baseline chargebacks |
| `high_disputed_amount_ratio` | disputed_amount / total_amount ≥ 20% | Financial exposure |
| `temporal_concentration` | ≥ 50% of txns within any 24-hour window | Activity burst |
| `repeated_user_merchant_relationship` | any pair with ≥ 3 transactions | Concentrated repeat activity |

> **Threshold Justification**: The 10% chargeback-rate threshold is approximately 6× the
> dataset-wide chargeback rate (~1.4%), chosen to identify genuinely anomalous concentrations
> rather than noise. The 20% disputed-ratio threshold identifies cases where disputed amounts
> are material relative to the transaction volume.

---

## 8. Cluster Risk Scoring

**Formula** (score range: 0–100):

```
cluster_risk_score = 100 × (
    0.25 × norm(max(max_user_risk, max_merchant_risk), 100)    ← ceiling risk
  + 0.20 × norm(max(avg_user_risk, avg_merchant_risk), 100)   ← average exposure
  + 0.20 × min(1, cluster_chargeback_rate)                    ← chargeback concentration
  + 0.15 × min(1, disputed_amount_ratio)                      ← financial exposure
  + 0.10 × temporal_concentration                             ← burst detection
  + 0.10 × min(1, max_pair_txns / 10)                         ← relationship repeat
)
```

Where `norm(x, max_val) = min(1, x / max_val)`.

**Risk Level Thresholds**:
- `HIGH`: score ≥ 70
- `MEDIUM`: score ≥ 40
- `LOW`: score < 40

**Design Rationale**: The formula deliberately avoids using a simple average
of member scores, which would dilute a concentrated elevated-risk relationship
within a large low-risk cluster. Instead, **maximum risk receives the highest
weight (25%)**, ensuring that a single high-risk merchant within a cluster
substantially elevates the cluster score.

---

## 9. Temporal Concentration

For each cluster, the fraction of cluster transactions falling within any
rolling 24-hour window is computed using a two-pointer scan:

```python
window = pd.Timedelta(hours=24)
max_in_window = max sliding window count
temporal_concentration = max_in_window / total_txn_count
```

A value ≥ 0.50 triggers the `temporal_concentration` signal (≥ 50% of cluster
transactions concentrated within a 24-hour period).

---

## 10. Chargeback Concentration

For each cluster:

| Metric | Formula | Range |
|--------|---------|-------|
| `cluster_chargeback_rate` | `chargebacked_transaction_count / n_transactions` | [0, 1] — always a valid fraction |
| `disputed_amount_ratio` | `cluster_disputed_amount / cluster_total_amount` | [0, ∞) |
| `chargeback_count` | Raw complaint-record count (preserved; can exceed `n_transactions` if one transaction has multiple records — **not used as rate numerator**) | ≥ 0 |
| `chargebacked_transaction_count` | Distinct transactions with ≥ 1 complaint record (binary M3 `has_chargeback`) | [0, n_transactions] |
| `n_transactions` | Raw transaction denominator (always preserved) | ≥ 1 |

**Definition note (corrected from initial version):** `cluster_chargeback_rate` uses
`chargebacked_transaction_count` as the numerator — the count of distinct transactions
with at least one chargeback record — consistent with M5/M6's `chargeback_transaction_count`.
A transaction with 2 complaint records counts as **1 chargebacked transaction**, giving a
maximum possible rate of 1.0 (100%). The raw `chargeback_count` (complaint records) is
preserved separately for analyst review.

Example: 1 transaction + 2 complaint records → `cluster_chargeback_rate = 1.0` (not 2.0),
`chargeback_count = 2`.

---

## 11. Limitations

1. **Dataset constraint**: In the current dataset every (user_id, merchant_id)
   pair has exactly 1 transaction. The `repeated_user_merchant_relationship`
   signal therefore never fires. This reflects the actual data, not an engine bug.

2. **Cold-start / small clusters**: Components with only 1 transaction and a 100%
   chargeback rate can score high. The minimum-evidence gate (≥ 2 signals) partially
   mitigates this, but the raw counts must be inspected before acting.

3. **No ground-truth label**: Risk scores are rule-based. Elevated scores do not
   constitute evidence of fraud. Human review is required.

4. **Retrospective nature**: All cluster signals are computed over the full
   retrospective dataset. Point-in-time limitations documented in M5/M6 apply here
   equally.

5. **Static graph**: The graph is constructed as a snapshot. Dynamic graph analysis
   (streaming, evolving clusters) is out of scope for M7.

---

## 12. Responsible Interpretation

> Investigation candidates should be reviewed by a qualified analyst before any
> action is taken. The cluster labels (`LOW`, `MEDIUM`, `HIGH`) describe the
> **concentration of behavioural risk signals**, not the probability of fraud.
> Never refer to any cluster as a "fraud ring", "criminal network", or similar.
