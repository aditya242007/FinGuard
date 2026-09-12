# FinGuard M4.1 — EDA Report

> **Disclaimer:** This analysis identifies behavioral patterns and risk signals.
> It does not establish confirmed fraud without ground-truth fraud labels.

## 1. Dataset Used

| Dataset | Rows | Columns |
| --- | --- | --- |
| finguard_transactions.csv | 20,000 | 70 |
| users_analytics.csv | 17,878 | 11 |
| merchants_analytics.csv | 8,051 | 16 |

Analysis covers transactions from **2026-01-01** to **2026-12-03** (337 days).

---

## 2. Transaction KPIs

| KPI | Value |
| --- | --- |
| Total Transactions | 20,000 |
| Total Amount (₹) | 239,232,643.30 |
| Average Amount (₹) | 11,961.63 |
| Median Amount (₹) | 12,218.01 |
| Min / Max Amount (₹) | -24,847.86 / 24,998.12 |
| Successful | 17,053 (85.26%) |
| Failed | 1,955 (9.78%) |
| Pending | 992 (4.96%) |
| Avg Txns per Day | 59.35 |
| Avg Value per Day (₹) | 709,889.15 |

---

## 3. Chargeback KPIs

| KPI | Value |
| --- | --- |
| Transactions with Chargebacks | 2,451 |
| Chargeback Rate | 12.255% |
| Total Disputed Amount (₹) | 6,342,602.86 |
| Avg Disputed Amount (₹) | 2,432.91 |
| Disputed Amount Ratio | 2.6512% of total transaction value |
| Avg Report Delay (hours) | 1256.78 |
| Median Report Delay (hours) | 846.16 |
| Disputes After 7 Days | 1,102 (44.96%) |

---

## 4. Data Quality Impact

| Issue | Count | Rate |
| --- | --- | --- |
| Missing UTR | 1,000 | 5.0% |
| Negative Amount | 420 | 2.1% |
| Invalid Timestamp | 0 | 0.0% |
| Unmatched KYC | 13,522 | 67.61% |
| Unmatched Merchant | 10,369 | 51.84% |
| Duplicate TXN ID | 0 | 0.0% |

---

## 5. Top Merchant Categories

| Category | Txns | Total Amount (₹) | Chargeback Count | CB Rate% |
| --- | --- | --- | --- | --- |
| TELECOM | 445 | 5,019,133 | 62 | 13.93 |
| RETAIL | 315 | 3,762,046 | 42 | 13.33 |
| DEPT_STORE | 288 | 3,557,063 | 31 | 10.76 |
| STATIONERY | 287 | 3,699,194 | 46 | 16.03 |
| HOTEL_LODGING | 280 | 3,517,310 | 32 | 11.43 |
| DEPARTMENT STORE | 277 | 3,413,731 | 28 | 10.11 |
| MOBILE RECHARGE | 261 | 3,244,348 | 30 | 11.49 |
| CLOTHS | 251 | 2,965,446 | 31 | 12.35 |
| TRANSPORT | 246 | 2,934,857 | 32 | 13.01 |
| MISCELLANEOUS | 241 | 3,077,814 | 24 | 9.96 |


---

## 6. Validation Results

| Check | Result |
| --- | --- |
| txn_count_equals_20000 | ✅ PASS |
| no_row_multiplication | ✅ PASS |
| success_rate_in_range | ✅ PASS |
| failure_rate_in_range | ✅ PASS |
| pending_rate_in_range | ✅ PASS |
| no_division_by_zero_kpi | ✅ PASS |
| chargeback_rate_nonnegative | ✅ PASS |
| disputed_ratio_nonnegative | ✅ PASS |
| daily_total_reconciles | ✅ PASS |
| status_rates_sum_le100 | ✅ PASS |

**OVERALL: ✅ PASS**

---

## 7. Methodology

- **Denominators:** All rates use the full transaction count (20,000) as denominator unless stated otherwise.
- **Missing data:** Rows with null amounts/timestamps are excluded from numeric aggregations only. Row counts always include all records.
- **Outliers:** IQR (3× fence) and z-score (|z|>3) flagging applied but outliers are retained.
- **Anomaly labeling:** All identified patterns are labeled "risk signal" or "anomaly", never "fraud".
- **Chargeback rate:** transactions_with_chargeback / total_transactions
- **Disputed amount ratio:** total_disputed_amount / total_transaction_amount
