# FinGuard M5 Feature Dictionary

This dictionary categorizes all features generated during M5 Feature Engineering.
**Crucially, features are classified by their temporal availability to prevent target leakage during M6 modeling.**

## Leakage Classifications
* **TRANSACTION-TIME**: Available at the exact moment the transaction is processed. Safe for real-time scoring.
* **POST-EVENT (RETROSPECTIVE)**: Only available *after* the transaction has completed (e.g., chargebacks). **Must NOT be used to predict fraud for the transaction itself.** Useful for investigations, clustering, or target creation.
* **AGGREGATED BEHAVIORAL**: Historical aggregations up to the current dataset boundary.
  > [!WARNING]
  > Global user/merchant aggregates are retrospective features. They must not be used as transaction-time predictors without point-in-time reconstruction.

---

### Transaction Level Features (`transaction_risk_features.csv`)

| Feature | Description | Leakage Class | Notes |
|---------|-------------|---------------|-------|
| `amount_numeric` | Absolute transaction value | TRANSACTION-TIME | Includes negative values |
| `amount_abs` | Absolute transaction value | TRANSACTION-TIME | |
| `amount_percentile` | Rank percentile of amount across all transactions | AGGREGATED BEHAVIORAL | |
| `amount_iqr_anomaly_flag` | True if amount > Q3 + 3*IQR | AGGREGATED BEHAVIORAL | |
| `transaction_hour` | Hour of the day | TRANSACTION-TIME | |
| `day_of_week` | Day of the week (0-6) | TRANSACTION-TIME | |
| `success_flag` | Status is SUCCESS | NEAR-TIME | |
| `failed_flag` | Status is FAILED | NEAR-TIME | |
| `timestamp_invalid_flag` | Data-quality signal indicating invalid or anomalous timestamp information. | TRANSACTION-TIME | DQ signal |
| `missing_utr_flag` | Transaction/data-quality signal indicating missing UTR and potentially reduced reconciliation/traceability. | TRANSACTION-TIME | DQ signal |
| `duplicate_txn_id_flag` | Normalized TXN ID is duplicated | TRANSACTION-TIME | DQ signal |
| `has_chargeback` | Whether the transaction was disputed | POST-EVENT | **LEAKAGE DANGER** |
| `chargeback_report_delay_hours` | Hours between txn and dispute | POST-EVENT | **LEAKAGE DANGER** |
| `invalid_chargeback_delay_flag` | True if report delay < 0 | POST-EVENT | DQ signal |
| `user_amount_zscore` | Z-score of txn amount relative to user mean | AGGREGATED BEHAVIORAL | Requires N>=5 |
| `merchant_amount_zscore` | Z-score of txn amount relative to merchant mean | AGGREGATED BEHAVIORAL | Requires N>=5 |

---

### User Level Features (`user_risk_features.csv`)

| Feature | Description | Leakage Class | Notes |
|---------|-------------|---------------|-------|
| `transaction_count` | Total transactions by user | AGGREGATED BEHAVIORAL | |
| `total_transaction_amount` | Sum of all transaction amounts | AGGREGATED BEHAVIORAL | |
| `amount_std` | Standard deviation of transaction amounts | AGGREGATED BEHAVIORAL | |
| `success_rate` | successful / total | AGGREGATED BEHAVIORAL | |
| `failure_rate` | failed / total | AGGREGATED BEHAVIORAL | |
| `chargeback_rate` | txns with chargeback / total | POST-EVENT | **LEAKAGE DANGER** |
| `total_disputed_amount` | Sum of disputed amounts | POST-EVENT | **LEAKAGE DANGER** |
| `dispute_after_7_days_rate` | late disputes / total disputes | POST-EVENT | **LEAKAGE DANGER** |
| `unique_merchant_count` | Number of distinct merchants transacted with | AGGREGATED BEHAVIORAL | |
| `kyc_status` | KYC verification status | TRANSACTION-TIME | Assuming static KYC |
| `kyc_duplicate_entity_flag` | True if KYC info maps to multiple users | TRANSACTION-TIME | DQ signal |

---

### Merchant Level Features (`merchant_risk_features.csv`)

| Feature | Description | Leakage Class | Notes |
|---------|-------------|---------------|-------|
| `transaction_count` | Total transactions at merchant | AGGREGATED BEHAVIORAL | |
| `total_transaction_amount` | Sum of all transaction amounts | AGGREGATED BEHAVIORAL | |
| `success_rate` | successful / total | AGGREGATED BEHAVIORAL | |
| `failure_rate` | failed / total | AGGREGATED BEHAVIORAL | |
| `chargeback_rate` | txns with chargeback / total | POST-EVENT | **LEAKAGE DANGER** |
| `disputed_amount_ratio` | disputed amount / total amount | POST-EVENT | **LEAKAGE DANGER** |
| `unique_user_count` | Number of distinct users transacted | AGGREGATED BEHAVIORAL | |
| `merchant_status` | Status from merchant master | TRANSACTION-TIME | |
| `mcc` | Merchant Category Code | TRANSACTION-TIME | |
| `merchant_duplicate_entity_flag` | True if PAN maps to multiple merchants | TRANSACTION-TIME | DQ signal |

---

### Chargeback Features (`chargeback_risk_features.csv`)

| Feature | Description | Leakage Class | Notes |
|---------|-------------|---------------|-------|
| `txn_id_normalized` | Primary key | N/A | |
| `total_disputed_amount` | Amount disputed in this complaint | POST-EVENT | |
| `chargeback_report_delay_hours` | Hours since transaction | POST-EVENT | |
| `invalid_chargeback_delay_flag` | True if delay is negative | POST-EVENT | DQ signal |
| `dispute_after_7_days_flag` | True if delay > 168 hours | POST-EVENT | |

---
**Methodology Notes:**
* Relative anomalies (Z-scores) use a `min_n=5` threshold. Entities with fewer than 5 transactions yield `NaN`.
* Negative transaction amounts are retained across all aggregations as valid behavior/DQ signals.
* Rate denominators are always explicitly guarded against divide-by-zero errors.
