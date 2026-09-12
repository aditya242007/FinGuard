# FinGuard M6 Risk Engine Methodology

## 1. Objective

Build a deterministic, explainable risk-scoring framework for FinGuard UPI transactions, users, and merchants that:

- Identifies elevated-risk patterns and behavioral anomalies
- Produces investigation candidates
- Provides fully human-readable explanations for every score
- Does **NOT** claim confirmed fraud
- Does **NOT** output a "fraud probability"

There is **no ground-truth fraud label** in this dataset. The engine is therefore purely rule-based and business-justified.

---

## 2. Why No Supervised Fraud Model

A supervised model requires a validated fraud label. In this dataset the closest available signal is `has_chargeback`, which represents a *disputed* transaction — not necessarily a fraudulent one. Optimizing model weights against chargeback outcomes would:

- Introduce undeclared target leakage
- Conflate dispute risk with fraud risk
- Produce over-optimistic performance metrics
- Make the model unauditable and uninterpretable

The rule-based engine is the correct tool for this milestone. A supervised model can be considered separately if a validated fraud label becomes available in a later phase.

---

## 3. Scoring Modes

The engine maintains a **strict separation** between two scoring modes that must never be mixed.

### Mode A — Transaction-Time Risk

Uses only information available **at or before** the moment of the transaction. Implements point-in-time feature calculation to prevent leakage of future data.

**Safe signals:**
- Data-quality signals on the transaction itself (missing UTR, invalid timestamp)
- User KYC status (treated as static at transaction time)
- Point-in-time historical user failure rate (calculated using only prior transactions via `.shift(1).expanding()`)
- Point-in-time user amount anomaly Z-score relative to prior history

**Explicitly excluded from transaction-time scoring:**
- `has_chargeback` for the current transaction
- `chargeback_rate` (global aggregate — includes future chargebacks)
- `total_disputed_amount`
- `dispute_after_7_days_flag`
- Any future transaction aggregates

### Mode B — Retrospective Investigation Risk

May use full historical aggregates and post-event chargeback information. Clearly labeled as **RETROSPECTIVE**. Useful for investigations, merchant review, user review, and post-event analysis. **Not valid transaction-time predictors.**

---

## 4. Signal Registry

### Transaction-Time Signals

| Signal Name | Entity | Weight | Max Contribution | Logic | Rationale |
|---|---|---|---|---|---|
| `missing_utr` | Transaction | 15 | 15 | Boolean flag | DQ signal: missing UTR reduces reconciliation traceability |
| `invalid_timestamp` | Transaction | 10 | 10 | Boolean flag | DQ signal: anomalous timestamp information |
| `kyc_rejected_unverified` | User→Txn | 25 | 25 | 1.0 if REJECTED/UNVERIFIED | KYC failure correlates with elevated identity risk |
| `amount_anomaly_user_relative` | Transaction | 25 | 25 | Z-score clipped to [0,3]/3 | Unusually large amount relative to user's own history |
| `historical_user_failure_rate` | User (PIT) | 25 | 25 | Expanding mean shifted-by-1 | Elevated prior failure rate signals credential or payment issues |

**Total max transaction-time score weight: 100**

### Retrospective Signals

| Signal Name | Entity | Weight | Max Contribution | Logic | Rationale |
|---|---|---|---|---|---|
| `user_chargeback_rate` | User | 35 | 35 | Direct ratio (0–1) | Primary post-event dispute signal for users |
| `merchant_chargeback_rate` | Merchant | 35 | 35 | Direct ratio (0–1) | Primary post-event dispute signal for merchants |
| `merchant_disputed_amount_ratio` | Merchant | 25 | 25 | Disputed/total amounts | Financial exposure relative to volume |
| `user_delayed_dispute_rate` | User | 15 | 15 | Late disputes / total disputes | Late reporting may indicate account takeover or delayed fraud detection |
| `merchant_delayed_dispute_rate` | Merchant | 15 | 15 | Late disputes / total disputes | Same pattern at merchant level |
| `kyc_duplicate_entity_flag` | User | 10 | 10 | Boolean flag | Multiple users sharing KYC details — identity risk signal |
| `user_failure_rate` | User | 15 | 15 | Failed/total txns | Elevated payment failure frequency |
| `merchant_failure_rate` | Merchant | 15 | 15 | Failed/total txns | Elevated merchant-side failure frequency |

**User retrospective max weight: 75** (chargeback_rate + failure_rate + delayed_dispute_rate + kyc_dup)  
**Merchant retrospective max weight: 90** (chargeback_rate + disputed_amount_ratio + failure_rate + delayed_dispute_rate)

---

## 5. Weight Methodology

Weights were assigned based on **business relevance**, not statistical optimization against chargeback outcomes.

| Priority | Rationale |
|---|---|
| **High (25–35)** | Signals with direct, defensible links to risk behaviour (KYC rejection, chargeback rate, disputed amount) |
| **Medium (15–25)** | Strong behavioral signals that may have innocent explanations (amount anomaly, failure rate) |
| **Low (10–15)** | Data-quality and contextual signals (missing UTR, invalid timestamp, delayed disputes, KYC duplicate) |

**No signal dominates the score:** In the transaction-time mode, the maximum any single signal contributes is 25 out of 100 (25%). In retrospective mode, the chargeback rate is capped at 35 out of the total possible weight.

---

## 6. Normalization Methodology

| Signal Type | Normalization |
|---|---|
| **Boolean flags** | 0.0 or 1.0 — no transformation needed |
| **Rate signals (0–1)** | Used directly — already bounded |
| **Z-score anomaly** | Z-score clipped to [0, 3], divided by 3 → [0, 1] |

All signals are normalized to [0, 1] before applying weights.

**Score formula:**

```
score = Σ(normalized_signal × weight)
risk_score = 100 × (score / max_possible_weight)
risk_score = clip(risk_score, 0, 100)
```

---

## 7. Risk-Level Thresholds

| Score Range | Risk Level |
|---|---|
| 0–29 | LOW |
| 30–59 | MEDIUM |
| 60–79 | HIGH |
| 80–100 | CRITICAL |

> [!WARNING]
> These thresholds are **analytical investigation categories**, not statistically calibrated fraud probabilities. A score of 80 does NOT mean "80% probability of fraud." The thresholds exist to help prioritize investigation resources.

---

## 8. Explainability

Every scored entity contains:

- `risk_score` — numerical 0–100
- `risk_level` — LOW / MEDIUM / HIGH / CRITICAL
- `top_risk_signal_1` — highest-contributing signal name
- `top_risk_signal_2` — second-highest
- `top_risk_signal_3` — third-highest
- `explanation` — auto-generated human-readable text

**Example output:**

> "Elevated risk driven primarily by kyc rejected unverified, combined with missing utr."

---

## 9. Temporal Leakage Controls

### Point-in-Time Calculation

For every transaction at time T, the historical user failure rate and amount baseline are calculated using only records with `timestamp < T`:

```python
df.groupby("user_id_normalized")["failed_flag"].transform(
    lambda x: x.shift(1).expanding().mean()
)
```

The `.shift(1)` ensures the current transaction is never included in its own historical baseline.

### Explicit Exclusions from Transaction-Time Mode

The following features exist in M5 outputs but are **explicitly excluded** from transaction-time scoring and placed in retrospective scoring only:

- `has_chargeback`
- `chargeback_rate`
- `total_disputed_amount`
- `dispute_after_7_days_flag`
- `user_transaction_count` (global — includes future)
- `merchant_transaction_count` (global — includes future)

---

## 10. Cold-Start Handling

When a user has fewer than 5 prior transactions (point-in-time count), behavioral signals are **scaled down** proportionally:

```
cold_start_factor = min(N / 5, 1.0)
contribution = contribution × cold_start_factor
```

This means:
- A user's first transaction contributes 0 from behavioral signals
- A user's 3rd transaction contributes 60% of the behavioral signal weight
- At 5+ transactions, full contribution applies

Cold-start users do **NOT** automatically receive a high risk score. Only data-quality signals (missing UTR, KYC status) apply at full weight from the first transaction.

---

## 11. Missing Data Handling

| Missing Data | Treatment |
|---|---|
| Missing KYC match | KYC signal set to 0 — not automatically a risk signal |
| Missing merchant match | Merchant signal set to 0 — not automatically a risk signal |
| Missing UTR | `missing_utr_flag = True` — treated as a **data-quality signal**, not fraud |
| Missing chargeback data | Rates set to 0.0 via `.fillna(0.0)` |
| Missing amount | `amount_abs` used — 0.0 if missing |

**Missing data ≠ fraud.** Data quality signals are weighted lower than behavioral signals.

---

## 12. Signal Correlation and Redundancy

Several signals in the retrospective mode measure related phenomena:

| Signal Pair | Overlap | Handling |
|---|---|---|
| `chargeback_rate` + `disputed_amount_ratio` | Both capture dispute exposure | Given different weights (35 vs 25); ratio captures financial severity, rate captures frequency |
| `chargeback_rate` + `delayed_dispute_rate` | Both post-event | Measure different dimensions: frequency vs timing |
| `user_failure_rate` + `merchant_failure_rate` | Applied at different entity levels | Applied separately to user and merchant scoring |

No pair is given maximum weight simultaneously. The engine avoids blindly stacking correlated signals.

---

## 13. Limitations

1. **No ground-truth validation:** Without confirmed fraud labels, it is impossible to validate recall or precision.
2. **Global aggregates remain retrospective:** Even with point-in-time logic for transactions, user and merchant scores use full dataset aggregates.
3. **Chargeback ≠ fraud:** Dispute data may include legitimate disputes. The engine treats them as behavioral signals only.
4. **Static KYC assumption:** KYC status is treated as static at transaction time. In reality, KYC status may have changed after the transaction.
5. **Dataset boundary effects:** Point-in-time calculations are limited by the available dataset date range. Very early transactions in the dataset have limited history.

---

## 14. Responsible Interpretation

> [!IMPORTANT]
> This risk engine produces **investigation priorities**, not fraud verdicts.

- **Do NOT** use these scores as the sole basis for account suspension, transaction blocking, or legal action.
- **Do NOT** interpret risk level as a probability statement about fraud.
- **Do** use these scores to prioritize investigation queues and manual review.
- **Do** review the top contributing signals alongside the score before acting.
- **Do** treat CRITICAL merchants/users as requiring investigation, not as confirmed fraud cases.
