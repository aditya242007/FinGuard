# M7 Read-Only Audit Report

**Date:** 2026-09-13  
**Scope:** Read-only review. No code, scores, outputs, or methodology were modified.

---

## 1. Cluster Chargeback Rate — Exact Denominator

### What M7 computes

```
cluster_chargeback_rate = SUM(finguard_transactions.chargeback_count)
                          ─────────────────────────────────────────────
                          COUNT(transactions in the cluster)
```

The **numerator** (`chargeback_count`) comes from `finguard_transactions.chargeback_count`,
which was populated during the M3 join as the **count of chargeback complaint records**
linked to each transaction (not a binary 0/1 flag).

The **denominator** (`transaction_count` in `user_merchant_relationships.csv`) is the
raw count of transaction rows in the cluster, produced by `groupby.agg(count)` on
`txn_id_normalized`.

Source lines: [`m7_graph_analysis.py L207–L220`](file:///Volumes/KRISH/DATATHON/FinGuard/src/risk/m7_graph_analysis.py#L207-L220)

```python
chargeback_count=("chargeback_count", "sum"),   # ← SUM of CB records, not distinct txns
```

---

## 2. Comparison with M5/M6 Chargeback Rate Definition

| Property | M5/M6 Definition | M7 Definition |
|---|---|---|
| Numerator | `chargeback_transaction_count` — COUNT DISTINCT txn_ids with ≥1 CB record | SUM of `finguard_transactions.chargeback_count` — total CB complaint records |
| Denominator | Total transaction count | Total transaction count |
| Possible range | [0, 1] — a true rate | [0, ∞) — CAN exceed 1.0 |
| Columns used | M5 `merchant_risk_features.chargeback_transaction_count` | M3 join `finguard_transactions.chargeback_count` |

**Finding:** M7's `cluster_chargeback_rate` uses a **different numerator** than M5/M6's
`chargeback_rate`. M5/M6 count distinct *transactions* with a chargeback; M7 counts
total chargeback *complaint records*. This is a **definitional inconsistency** across
milestones, not a mathematical error in isolation.

**Impact:** 13 out of 655 clusters (2.0%) have `cluster_chargeback_rate > 1.0`, which
is mathematically impossible for a true rate. These 13 clusters contain transactions
with multiple complaint records against a single transaction.

---

## 3. CLU00604 Investigation — 1 Transaction, 2 Chargebacks, 200%

### Data facts (read-only)

| Field | Value |
|---|---|
| cluster_id | CLU00604 |
| user | USR40970 |
| merchant | MCH6502 |
| Transactions | 1 (`TXN00006755`) |
| Transaction amount | ₹45.69 |
| `finguard_transactions.chargeback_count` | **2.0** |
| `finguard_transactions.total_disputed_amount` | 1,246.53 |
| Chargeback records linked | **2** (`CBK0000266`, `CBK0001010`) |

### The two chargeback records

| complaint_id | disputed_amount | severity | resolution_status | reported_timestamp |
|---|---|---|---|---|
| CBK0000266 | 1,874.00 | MEDIUM | CLOSED | 2026-01-07 |
| CBK0001010 | **−627.47** | LOW | PENDING_BANK | 2026-03-17 |

### What this means

1. **TXN00006755 is ONE transaction** — not two separate transactions.
2. **Two complaint records exist** against this single transaction. The second
   (`CBK0001010`) has a **negative disputed amount (−627.47)**, which in M4 context
   was identified as a data-quality or potential reversal-type record, **not** a
   confirmed second fraudulent chargeback.
3. M7's 200% rate (= 2 CB records / 1 transaction) **does not mean 200% of
   transactions were chargebacked**. It means 2 complaint records were filed against
   1 transaction.
4. M6 correctly scored MCH6502's chargeback rate at **100%** (1 chargebacked
   transaction / 1 total transaction) because M6 uses the binary `has_chargeback`
   count.

### Is the 200% semantically intentional?

**No.** The 200% figure is an artefact of using `SUM(chargeback_count)` in the
numerator. It reflects the count of complaint records, not the fraction of transactions
with chargebacks. The correct rate for this cluster — if aligned with M5/M6 semantics
— would be **100%** (1 out of 1 transaction is chargebacked), which is still the
highest possible rate and equally alarming.

### Does this cause incorrect classification?

**Partially.** The cluster is correctly flagged as HIGH-risk regardless: MCH6502
has a 100% chargeback rate in M6 and a ≥ 20% disputed-amount ratio. The elevated
score is justified by real signals. However, the `cluster_chargeback_rate = 2.0`
**overstates the rate** in a semantically misleading way and introduces inconsistency
with M5/M6 baseline comparisons.

**This is flagged as a known issue to correct in the next revision.**

---

## 4. Single-Transaction Multi-Chargeback Misinterpretation Risk

The audit confirms:

- `finguard_transactions.chargeback_count` can be ≥ 2 for a **single transaction**.
- 151 transactions in the dataset have `chargeback_count ≥ 2`.
- M7 sums this field, so a single transaction with 2 complaint records adds 2 to
  the cluster's numerator while adding only 1 to the denominator.
- This is **not** the same as 2 separate transactions being chargebacked.
- M7 does **not** fabricate chargeback records; it reads the M3-computed
  `chargeback_count` field faithfully.

**Conclusion:** The computation is internally consistent but is using the wrong
semantic definition of "chargeback rate". The score does not misrepresent the
underlying data records; it misrepresents what the rate means in plain English.

---

## 5. 655 Investigation-Candidate Filtering Logic

### Gate applied (code-verified)

```python
signals_present = []
if avg_user_risk >= 15:    signals_present.append("elevated_avg_user_risk")
if max_user_risk >= 25:    signals_present.append("elevated_max_user_risk")
if avg_merch_risk >= 25:   signals_present.append("elevated_avg_merchant_risk")
if cluster_chargeback_rate >= 0.10: signals_present.append("high_cluster_chargeback_rate")
if disputed_ratio >= 0.20: signals_present.append("high_disputed_amount_ratio")
if temp_conc >= 0.50:      signals_present.append("temporal_concentration")
if max_pair_txns >= 3:     signals_present.append("repeated_user_merchant_relationship")

if len(signals_present) < 2:
    return None  # excluded
```

### Signal frequency across 655 clusters

| Signal | Clusters containing it |
|---|---|
| `high_cluster_chargeback_rate` | 655 (100%) |
| `temporal_concentration` | 403 (61.5%) |
| `high_disputed_amount_ratio` | 252 (38.5%) |
| `elevated_avg_merchant_risk` | 126 (19.2%) |
| `elevated_avg_user_risk` | 22 (3.4%) |
| `elevated_max_user_risk` | 19 (2.9%) |

### Observation

**Every one of the 655 clusters is triggered by `high_cluster_chargeback_rate`.**
This means the minimum-evidence gate effectively requires 1 additional signal beyond
the chargeback-rate signal. Given the definitional issue in Section 2–4 above —
where `cluster_chargeback_rate` can exceed 1.0 for transactions with multiple
complaint records — some clusters may have passed the 10% gate **only because of
the inflated numerator**, not because of a genuinely elevated chargeback fraction.

However, 403 of the 655 also show `temporal_concentration` and 252 show
`high_disputed_amount_ratio`, meaning the majority have genuine multi-signal support.

**This is flagged for resolution in a future revision of the cluster rate definition.**

---

## 6. Risk Level Band Consistency

| Band | Score Threshold | Labeled Count | Score Count | Match |
|---|---|---|---|---|
| HIGH | ≥ 70 | 1 | 1 | ✅ |
| MEDIUM | ≥ 40 and < 70 | 46 | 46 | ✅ |
| LOW | < 40 | 608 | 608 | ✅ |
| CRITICAL | ≥ 90 (if added) | 0 | 0 | ✅ |

Labels are **exactly consistent** with the documented score bands. No miscoded labels.

---

## 7. No Fabricated Relationships

Verified read-only:

| Check | Result |
|---|---|
| All USER node_ids in `graph_nodes.csv` exist in `finguard_transactions.user_id_normalized` | ✅ |
| All MERCHANT node_ids exist in `finguard_transactions.merchant_id_normalized` | ✅ |
| All TRANSACTION node_ids exist in `finguard_transactions.txn_id_normalized` | ✅ |
| All CHARGEBACK node_ids exist in `chargebacks_clean.complaint_id_normalized` | ✅ |
| No fuzzy matching used in `m7_graph_analysis.py` | ✅ (confirmed by code review) |
| No guessed identities | ✅ |
| Edges created only where both source and target exist | ✅ |

---

## 8. Scores Are Retrospective / Not Fraud Probabilities

Verified:

- The methodology document (`m7_graph_methodology.md`) states explicitly: *"scores
  describe the concentration of behavioural risk signals, not the probability of
  fraud."*
- Output column is named `cluster_risk_score`, not `fraud_probability` or
  `fraud_score`.
- All cluster explanations use the phrase *"Investigation candidate due to…"* — no
  cluster is called a fraud ring, criminal network, or confirmed fraud.
- No ground-truth label was introduced.

---

## 9. Top Cluster Explanation is Evidence-Based

CLU00604 explanation (verbatim from CSV):

> *"Investigation candidate due to: elevated_avg_merchant_risk, high_cluster_chargeback_rate,
> high_disputed_amount_ratio. Cluster involves 1 user(s) and 1 merchant(s) with
> 1 transaction(s), chargeback rate 200.0%, disputed amount ratio 2728.2%."*

Evidence basis:

| Claim | Supporting fact |
|---|---|
| `elevated_avg_merchant_risk` | MCH6502 M6 retro score = 100.0 (CRITICAL) ✅ |
| `high_cluster_chargeback_rate` | 2 CB records / 1 txn = 200% (> 10% gate) ✅ (see definitional note) |
| `high_disputed_amount_ratio` | ₹1,246.53 disputed / ₹45.69 txn = 27.28 (> 20% gate) ✅ |

**All three signal claims are traceable to data.** The 200% rate is technically accurate
(it is the computed ratio) but semantically misleading as documented above.

---

## 10. Known Issues Identified

| # | Issue | Severity | Requires Fix? |
|---|---|---|---|
| 1 | `cluster_chargeback_rate` uses SUM(CB records) / txn count, not COUNT(txn with CB) / txn count. Inconsistent with M5/M6 definition. Rate can exceed 1.0. | **Medium** | ✅ Fix in next revision |
| 2 | 13 clusters (2.0%) report `cluster_chargeback_rate > 1.0`, which is semantically misleading. The 655 candidate count and HIGH/MEDIUM/LOW assignments may shift after correction. | **Medium** | ✅ Fix in next revision |
| 3 | `repeated_user_merchant_relationship` signal never fires in this dataset (all pairs have exactly 1 transaction). This is a data characteristic, not a code error. | Low | Document only |
| 4 | Negative disputed amounts in CB records are summed into `total_disputed_amount` without flagging. CLU00604's two CB records include CBK0001010 with −627.47. | Low | Document only |

---

## Summary

**M7 AUDIT: INVESTIGATE**

The graph is structurally sound — nodes, edges, IDs, reconciliation, score bands, and
explainability are all correct. However, **one definitional issue** requires a fix
before M7 can be marked fully clean:

> The `cluster_chargeback_rate` numerator must use **COUNT of transactions with
> ≥ 1 chargeback** (consistent with M5/M6's `chargeback_transaction_count`), not
> **SUM of chargeback complaint records** per transaction.
>
> 13 clusters (2.0%) currently report rates > 100%, which is mathematically
> impossible for a true fraction and semantically incorrect.

No code, scores, or outputs were modified during this audit.
