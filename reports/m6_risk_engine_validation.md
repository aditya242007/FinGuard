# FinGuard M6 Risk Engine Validation Report

## A. Score Range

| Entity | Score Type | Min | Max | NaN Count | Inf Count |
|---|---|---|---|---|---|
| Transaction | Transaction-Time | 0.0 | 40.0 | 0 | 0 |
| Transaction | Retrospective | 0.0 | 100.0 | 0 | 0 |
| User | Retrospective | 0.0 | 33.33 | 0 | 0 |
| Merchant | Retrospective | 0.0 | 100.0 | 0 | 0 |

✅ All scores within [0, 100]. No NaN. No Infinity.

---

## B. Risk Level Distribution

### Transaction-Time Risk Levels

| Risk Level | Count |
|---|---|
| LOW | 19,976 |
| MEDIUM | 24 |
| HIGH | 0 |
| CRITICAL | 0 |

### Retrospective Risk Levels (Merchants)

| Risk Level | Count |
|---|---|
| LOW | 7,946 |
| MEDIUM | 101 |
| HIGH | 3 |
| CRITICAL | 1 |

### Retrospective Risk Levels (Users)

| Risk Level | Count |
|---|---|
| LOW | 17,876 |
| MEDIUM | 2 |

---

## C. Row Conservation & Entity Uniqueness

| File | Rows | Unique IDs | Match Source |
|---|---|---|---|
| `transaction_risk_scores.csv` | 20,000 | 20,000 | ✅ Matches M3 source exactly |
| `user_risk_scores.csv` | 17,878 | 17,878 | ✅ Matches M5 user features |
| `merchant_risk_scores.csv` | 8,051 | 8,051 | ✅ Matches M5 merchant features |

No join explosion detected. No duplicate entity IDs.

---

## D. Temporal Leakage Check

### Test: `has_chargeback` does NOT influence transaction-time score

The test `TestTemporalLeakage::test_chargeback_not_used_in_tt_score` creates two synthetic transactions identical in every field except `has_chargeback` (0 vs 1) and verifies their transaction-time scores are identical.

**Result: ✅ PASS** — chargeback outcome has zero influence on transaction-time scoring.

### Transaction-time signals verified to contain NO post-event data:

| Signal | Post-Event Component | Status |
|---|---|---|
| `missing_utr` | None | ✅ Clean |
| `invalid_timestamp` | None | ✅ Clean |
| `kyc_rejected_unverified` | None (static KYC) | ✅ Clean |
| `amount_anomaly_user_relative` | Uses only `timestamp < T` history | ✅ Clean |
| `historical_user_failure_rate` | Uses only `timestamp < T` via `.shift(1)` | ✅ Clean |

---

## E. Point-in-Time Logic Validation

### Test: First transaction has zero historical failure rate

A synthetic user's first-ever transaction is verified to have `historical_user_failure_rate = 0.0` (no prior observations).

**Result: ✅ PASS**

### Test: Second transaction uses only the first transaction's data

A synthetic 2-transaction sequence (first failed, second succeeded) is verified to give the second transaction a historical failure rate of 1.0 (the first transaction's result), not 0.5 (the full average including the current).

**Result: ✅ PASS**

---

## F. Cold-Start Handling

### Test: Cold-start scaling applied correctly

A user with 3 prior transactions receives a cold-start factor of `3/5 = 0.6`, reducing behavioral signal contributions proportionally. Verified the expanding cumcount and failure rate are calculated correctly.

**Result: ✅ PASS** — Cold-start does NOT automatically inflate scores.

---

## G. Missing Data Handling

- Missing KYC match → signal contribution = 0 (not a risk signal)
- Missing merchant match → signal contribution = 0
- Missing UTR → `missing_utr_flag = True` → DQ signal at weight 15 only
- Missing chargeback data → rates set to 0.0 via `fillna(0.0)`

**Result: ✅ No missing data causes artificial score inflation**

---

## H. Safe Division

### Test: User with all-zero rates scores exactly 0

A synthetic user with `chargeback_rate=0`, `failure_rate=0`, `dispute_after_7_days_rate=0`, `kyc_duplicate=False` verified to return score 0.0.

**Result: ✅ PASS**

### Test: Merchant with all-zero rates scores exactly 0

Same test for merchant entity.

**Result: ✅ PASS**

---

## I. Determinism

Running the full engine twice on identical inputs produces bit-for-bit identical scores.

**Result: ✅ PASS** — Max numerical difference across all output files = 0.0

---

## J. Retrospective / Transaction-Time Separation

Signal registry modes verified to have **zero overlap** in signal names.

Transaction output contains both `transaction_time_risk_score` and `retrospective_risk_score` as separate columns.

**Result: ✅ PASS**

---

## K. Explainability Coverage

All transactions and users with a positive score (> 0) have a non-empty explanation string.

**Result: ✅ PASS**

---

## L. Pytest Summary

**35 / 35 tests passed** in 18.27 seconds.

| Test Class | Tests | Status |
|---|---|---|
| `TestScoreBounds` | 4 | ✅ PASS |
| `TestNoNaN` | 4 | ✅ PASS |
| `TestNoInfinity` | 4 | ✅ PASS |
| `TestRiskLevels` | 4 | ✅ PASS |
| `TestRowConservation` | 3 | ✅ PASS |
| `TestEntityUniqueness` | 3 | ✅ PASS |
| `TestTemporalLeakage` | 1 | ✅ PASS |
| `TestPointInTime` | 2 | ✅ PASS |
| `TestColdStart` | 1 | ✅ PASS |
| `TestSafeDivision` | 2 | ✅ PASS |
| `TestModeSeparation` | 4 | ✅ PASS |
| `TestDeterminism` | 1 | ✅ PASS |
| `TestExplainability` | 2 | ✅ PASS |

---

## M. Top 20 Sanity Checks

### Top 10 Highest Transaction-Time Risk Transactions

All top transactions share the combination of **KYC REJECTED/UNVERIFIED** + **missing UTR**, producing a score of 40.0 (KYC weight 25 + UTR weight 15 = 40 out of 100 max). This is logically defensible: users with failed KYC attempting transactions without reconciliation trails are legitimate investigation candidates.

| txn_id | TT Score | Level | Signal 1 | Signal 2 |
|---|---|---|---|---|
| TXN00010418 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00006820 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00002216 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00007860 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00014473 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00009673 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00006769 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00002330 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00009068 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |
| TXN00016703 | 40.0 | MEDIUM | kyc_rejected_unverified | missing_utr |

### Top 10 Highest-Risk Users (Retrospective)

| user_id | Retro Score | Level | Chargeback Rate | Top Signal |
|---|---|---|---|---|
| USR56391 | 33.33 | MEDIUM | 0.25 | user_delayed_dispute_rate |
| USR63885 | 30.67 | MEDIUM | 1.00 | user_chargeback_rate |
| USR62336 | 29.33 | LOW | 0.33 | user_delayed_dispute_rate |
| USR22260 | 26.67 | LOW | 1.00 | user_chargeback_rate |
| USR27616 | 26.67 | LOW | 1.00 | user_chargeback_rate |
| USR34667 | 26.67 | LOW | 1.00 | user_chargeback_rate |
| USR35035 | 26.67 | LOW | 0.50 | user_chargeback_rate |
| USR35589 | 26.67 | LOW | 1.00 | user_chargeback_rate |
| USR45039 | 26.67 | LOW | 0.50 | user_chargeback_rate |
| USR51032 | 26.67 | LOW | 1.00 | user_chargeback_rate |

> [!NOTE]
> User scores are capped by cold-start scaling (most high-chargeback users have very few transactions, so the cold-start penalty reduces their scores). This correctly prevents 1-dispute-out-of-1-transaction users from dominating.

### Top 10 Highest-Risk Merchants (Retrospective)

| merchant_id | Retro Score | Level | Chargeback Rate | Disputed Ratio | Top Signal |
|---|---|---|---|---|---|
| MCH6502 | 100.0 | CRITICAL | 1.00 | 27.28 | merchant_disputed_amount_ratio |
| MCH5215 | 75.31 | HIGH | 1.00 | 11.56 | merchant_disputed_amount_ratio |
| MCH5863 | 64.51 | HIGH | 1.00 | 10.21 | merchant_disputed_amount_ratio |
| MCH3215 | 62.63 | HIGH | 0.50 | 1.52 | merchant_disputed_amount_ratio |
| MCH1820 | 51.20 | MEDIUM | 0.50 | 3.31 | merchant_disputed_amount_ratio |
| MCH4560 | 49.58 | MEDIUM | 1.00 | 6.92 | merchant_disputed_amount_ratio |
| MCH9375 | 47.22 | MEDIUM | 0.40 | 0.48 | merchant_chargeback_rate |
| MCH6858 | 44.38 | MEDIUM | 0.67 | 1.43 | merchant_disputed_amount_ratio |
| MCH6678 | 43.42 | MEDIUM | 0.75 | 0.15 | merchant_chargeback_rate |
| MCH9606 | 42.54 | MEDIUM | 0.50 | 0.31 | merchant_chargeback_rate |

> [!NOTE]
> MCH6502 scores CRITICAL (100.0) due to 100% chargeback rate AND a disputed-to-total-amount ratio of 27.28 (disputed amount exceeds total transaction amount — possible negative/reversal transactions in denominator). This is flagged for investigation, not declared fraud.

---

## N. Acceptance Criteria Checklist

| Criterion | Status |
|---|---|
| Transaction-time and retrospective scoring separated | ✅ |
| No chargeback leakage in transaction-time score | ✅ |
| Point-in-time logic implemented | ✅ |
| Risk scores are 0–100 | ✅ |
| Risk levels documented | ✅ |
| Every score is explainable | ✅ |
| Signal contributions available | ✅ |
| Signal weights documented | ✅ |
| No signal dominates without justification | ✅ |
| Correlated signals reviewed | ✅ |
| Cold-start handled | ✅ |
| Missing data handled correctly | ✅ |
| No division by zero | ✅ |
| No infinity | ✅ |
| No unexpected null scores | ✅ |
| No join explosion | ✅ |
| Entity uniqueness preserved | ✅ |
| Deterministic output | ✅ |
| Tests pass (35/35) | ✅ |
| Top-ranked entities manually sanity-checked | ✅ |
| No unsupported fraud claims | ✅ |
| M7 NOT started | ✅ |
