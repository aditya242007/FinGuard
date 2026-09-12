# FinGuard Data Quality Report

_Generated: 2026-09-12 17:09 UTC_

## Executive Summary

This report summarises the data quality audit for four raw datasets ingested into the FinGuard pipeline. **No data has been modified or deleted.** All findings are observations only.

- **Total issues detected:** 49
- **CRITICAL:** 4
- **HIGH:** 18
- **MEDIUM:** 27
- **LOW:** 14

### ⚠️ Critical Issues Requiring Immediate Attention

- **Duplicate user IDs (normalised)** — 13768 records
- **Duplicate merchant IDs (normalised)** — 3279 records
- **Duplicate complaint IDs** — 168 records
- **Transaction user_id not found in KYC (normalised)** — 13783 records

## Dataset Overview

| Dataset | Rows | Columns | Duplicate Rows |
| --- | --- | --- | --- |
| Transactions | 20400 | 8 | 400 |
| KYC Records | 36400 | 12 | 278 |
| Merchants | 6210 | 11 | 12 |
| Chargebacks | 2884 | 13 | 84 |

## Transaction Quality

### Missing Values

| Column | Missing Count | Missing % | Unique Values | Sample |
| --- | --- | --- | --- | --- |
| mcc | 2926 | 14.34% | 7 | 5411, 4131, 05411 |
| utr | 1024 | 5.02% | 19001 | UTR6498104698, UTR7656190355, UTR9037001889 |
| txn_id | 0 | 0.00% | 20000 | TXN00011869, TXN00010383, TXN00008297 |
| timestamp | 0 | 0.00% | 19083 | 2026-01-15 00:11:30, 2026-01-17 20:09:44, 2026-01-23 14:10:16 |
| user_id | 0 | 0.00% | 17878 | USR45826, USR79397, USR87810 |
| merchant_id | 0 | 0.00% | 8051 | MCH7045, MCH5031, MCH9809 |
| amount | 0 | 0.00% | 19900 | 15722.34, Rs. 6362.9, 15446.19 |
| status | 0 | 0.00% | 14 | COMPLETED, TXN_FAILED, S |

### Detected Issues

| Issue | Count | Percentage | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| Duplicate transaction IDs (txn_id) | 800 | 3.92% | HIGH | Investigate duplicates; during cleaning retain the earliest record or flag all as a ring-pattern if amounts differ. |
| Exact duplicate transaction rows | 400 | 1.96% | MEDIUM | Deduplicate exact rows in cleaning phase; keep one copy. |
| Blank txn_id | 0 | 0.00% | LOW | Records with blank txn_id cannot be joined or traced. Flag for quarantine review in Milestone 2. |
| Blank user_id | 0 | 0.00% | LOW | Records with blank user_id cannot be joined or traced. Flag for quarantine review in Milestone 2. |
| Blank merchant_id | 0 | 0.00% | LOW | Records with blank merchant_id cannot be joined or traced. Flag for quarantine review in Milestone 2. |
| Blank utr | 1024 | 5.02% | MEDIUM | Records with blank utr cannot be joined or traced. Flag for quarantine review in Milestone 2. |
| Amount — blank | 0 | 0.00% | LOW | Transactions with no amount are unusable; quarantine after review. |
| Amount — malformed | 0 | 0.00% | LOW | Strip currency symbols (Rs., ₹, INR) and parse to float in cleaning. |
| Amount — negative | 429 | 2.10% | HIGH | Negative amounts may represent reversals; flag and verify with status. |
| Amount — zero | 0 | 0.00% | LOW | Zero-amount transactions may be test rows; verify with merchant. |
| Timestamp — unix_epoch | 1012 | 4.96% | HIGH | Convert Unix epoch timestamps to ISO-8601 datetime in cleaning. |
| Timestamp — unparseable | 0 | 0.00% | LOW | Rows with unparseable timestamps cannot be time-series analysed; quarantine. |
| Timestamp — blank | 0 | 0.00% | LOW | Missing timestamps make time-series analysis impossible; quarantine. |
| Unusual MCC format | 0 | 0.00% | LOW | Normalise MCC to 4-digit numeric string; map MCC-XXXX prefix variants. |
| MCC with leading zero (5-digit) | 2938 | 14.40% | MEDIUM | Strip leading zero to standardise to 4-digit MCC. |

### Status Distribution

| Status Value | Count |
| --- | --- |
| S | 3538 |
| Success | 3501 |
| TXN_SUCCESS | 3490 |
| COMPLETED | 3477 |
| SUCCESS | 3389 |
| FAILED | 455 |
| TXN_FAILED | 416 |
| Fail | 395 |
| Declined | 376 |
| F | 348 |
| PENDING | 287 |
| PROCESSING | 266 |
| Pending | 236 |
| Initiated | 226 |

## KYC Quality

### Missing Values

| Column | Missing Count | Missing % | Unique Values | Sample |
| --- | --- | --- | --- | --- |
| date_of_birth | 2944 | 8.09% | 29285 | 06/04/1967 12:14 AM, 1969-02-19 08:25:23, 20/04/1961 |
| monthly_income | 2933 | 8.06% | 26035 | 35119, 80907, ₹11,214 |
| signup_timestamp | 2910 | 7.99% | 14608 | 2025-12-02 02:18:16, 01-31-2024, 2026-01-30 23:57:18 |
| aadhaar | 2664 | 7.32% | 32094 | 715658320763, 023412025028, 2781 6299 9816 |
| pan | 1896 | 5.21% | 33165 | SEJAA8194O, QT0ZZ5561X, QCNTL9489O |
| user_id | 0 | 0.00% | 32165 | USR16112, USR17216, USR 45454 |
| full_name | 0 | 0.00% | 33921 | Dhriti Deshmukh, Megha Jani, PANINI LAL |
| city | 0 | 0.00% | 41 | Bombay, Lucknow, kolkata |
| state | 0 | 0.00% | 9 | Maharashtra, Uttar Pradesh, West Bengal |
| occupation | 0 | 0.00% | 9 | Retired, Freelancer, Farmer |
| kyc_status | 0 | 0.00% | 16 | Done, Verified, Pending |
| risk_segment | 0 | 0.00% | 12 | LOW, medium, High |

### Detected Issues

| Issue | Count | Percentage | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| Duplicate user IDs (normalised) | 13768 | 37.82% | CRITICAL | Normalise user_id format and deduplicate; merge or flag duplicates. |
| Exact duplicate KYC rows | 278 | 0.76% | MEDIUM | Remove exact duplicate rows in cleaning. |
| Blank pan | 1896 | 5.21% | MEDIUM | Missing pan is a KYC compliance risk; flag records for manual review. |
| Blank aadhaar | 2664 | 7.32% | MEDIUM | Missing aadhaar is a KYC compliance risk; flag records for manual review. |
| Blank date_of_birth | 2944 | 8.09% | MEDIUM | Missing date_of_birth is a KYC compliance risk; flag records for manual review. |
| Blank monthly_income | 2933 | 8.06% | MEDIUM | Missing monthly_income is a KYC compliance risk; flag records for manual review. |
| Blank signup_timestamp | 2910 | 7.99% | MEDIUM | Missing signup_timestamp is a KYC compliance risk; flag records for manual review. |
| Inconsistent KYC status casing (16 raw variants → 13 normalised) | 12801 | 35.17% | MEDIUM | Normalise kyc_status to uppercase canonical values (e.g., VERIFIED, PENDING, REJECTED). |
| Inconsistent risk_segment casing (12 raw variants) | 24230 | 66.57% | MEDIUM | Normalise risk_segment to uppercase (HIGH, MEDIUM, LOW). |
| City capitalisation inconsistencies | 17153 | 47.12% | LOW | Title-case city during cleaning. |
| State capitalisation inconsistencies | 0 | 0.00% | LOW | Title-case state during cleaning. |
| Monthly income with currency symbol / k-suffix | 14004 | 38.47% | MEDIUM | Strip ₹, INR, Rs. and expand 'k' suffix; store as numeric. |
| Malformed monthly income (unparseable after symbol strip) | 1790 | 4.92% | HIGH | Manually review unparseable incomes; quarantine if unrecoverable. |

### KYC Status Distribution

| KYC Status | Count |
| --- | --- |
| Verified | 4862 |
| APPROVED | 4706 |
| VERIFIED | 4601 |
| KYC_DONE | 4587 |
| V | 4554 |
| Done | 4454 |
| PENDING | 1465 |
| Pending | 1032 |
| P | 1003 |
| IN_PROGRESS | 984 |
| Under Review | 983 |
| Rejected | 923 |
| R | 611 |
| REJECTED | 562 |
| Reject | 547 |
| FAILED | 526 |

## Merchant Quality

### Missing Values

| Column | Missing Count | Missing % | Unique Values | Sample |
| --- | --- | --- | --- | --- |
| settlement_account | 1252 | 20.16% | 3550 | 3021439858, NA, XXXX9523 |
| onboarding_date | 499 | 8.04% | 4400 | 09-23-2025, 10/01/2026, 14-Jan-2023 |
| mcc | 429 | 6.91% | 44 | MCC-7011, 5699, 5311 |
| declared_avg_ticket_size | 371 | 5.97% | 5521 | INR 2,432.18, 986.05, INR 1,427.52 |
| merchant_id | 0 | 0.00% | 5083 | mch2849, MCH4314, MCH1986 |
| merchant_name | 0 | 0.00% | 5732 | BHAVSAR, KOTA AND ZACHARIA, Deshmukh Ltd, Bains, Chanda and Gh0sh |
| merchant_category | 0 | 0.00% | 82 | hotel_lodging, Apparel, Retail |
| business_type | 0 | 0.00% | 14 | Private Limited, PRIVATE_LIMITED, individual |
| city | 0 | 0.00% | 41 | Ludhiana, Jalandhar, Jalandhar |
| state | 0 | 0.00% | 9 | Punjab, Punjab, Punjab |
| merchant_status | 0 | 0.00% | 15 | Inactive, I, A |

### Detected Issues

| Issue | Count | Percentage | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| Duplicate merchant IDs (normalised) | 3279 | 52.80% | CRITICAL | Normalise merchant_id format and deduplicate; retain most recent record. |
| Exact duplicate merchant rows | 12 | 0.19% | MEDIUM | Remove exact duplicate rows. |
| Blank MCC code | 429 | 6.91% | MEDIUM | MCC is required for regulatory category mapping; impute from merchant_category if possible. |
| MCC format — unusual | 771 | 12.42% | HIGH | Map non-standard MCC formats to 4-digit standard. |
| MCC format — dashed_prefix | 356 | 5.73% | MEDIUM | Strip 'MCC-' prefix; retain 4-digit code. |
| MCC format — leading_zero | 592 | 9.53% | MEDIUM | Strip leading zero from 5-digit MCC. |
| Missing onboarding date | 499 | 8.04% | MEDIUM | Onboarding date is required for merchant age analysis; flag for manual lookup. |
| Blank or invalid settlement account | 2451 | 39.47% | HIGH | Missing settlement account blocks payment; flag as HIGH risk. |
| Inconsistent merchant_category variants (82 raw → 44 normalised) | 5003 | 80.56% | MEDIUM | Standardise merchant_category to a controlled vocabulary. |
| Inconsistent merchant_status variants (15 raw → 12 normalised) | 3853 | 62.05% | MEDIUM | Standardise merchant_status to a controlled vocabulary. |
| Inconsistent business_type variants (14 raw → 8 normalised) | 3108 | 50.05% | MEDIUM | Standardise business_type to a controlled vocabulary. |
| Ticket size — negative | 501 | 8.07% | HIGH | Negative ticket sizes are invalid; verify or quarantine. |
| Ticket size — malformed | 0 | 0.00% | LOW | Strip INR/₹ prefix; convert to numeric. |

## Chargeback Quality

### Missing Values

| Column | Missing Count | Missing % | Unique Values | Sample |
| --- | --- | --- | --- | --- |
| bank_response_timestamp | 718 | 24.90% | 1149 | 2026-02-10 03:19:10, 12/03/2026 06:24 AM, 06/03/2026 |
| transaction_timestamp | 235 | 8.15% | 1238 | 2026/01/28, 25/02/2026 10:24 AM, 2026/02/04 |
| reported_timestamp | 209 | 7.25% | 1329 | 02-01-2026, 1772691855, 02-05-2026 |
| disputed_amount | 183 | 6.35% | 2609 | 414.69, Rs. 7,039, 1303.05 |
| txn_id | 81 | 2.81% | 2582 | TXN00004325, TXN00003720, TXN00012539 |
| complaint_id | 0 | 0.00% | 2800 | CBK0002082, CBK0001941, CBK0001799 |
| user_id | 0 | 0.00% | 2454 | usr97580, USR54113, USR17980 |
| merchant_id | 0 | 0.00% | 2051 | mch1127, 3835, mch3700 |
| reason_code | 0 | 0.00% | 34 | Merchant Not Delivered, login compromised, customer issue |
| complaint_text | 0 | 0.00% | 84 | Customer says amount was debited twice., User reports money deducted but merchant denies receiving payment., merchant service was not delivered after payment. |
| resolution_status | 0 | 0.00% | 13 | CLOSED, In Progress, OPEN |
| severity | 0 | 0.00% | 16 | Critical, H, P4 |
| channel | 0 | 0.00% | 8 | ivr, Call Center, IVR |

### Detected Issues

| Issue | Count | Percentage | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| Duplicate complaint IDs | 168 | 5.83% | CRITICAL | Investigate duplicate complaint IDs; may indicate system re-submission. |
| Duplicate txn_id in chargebacks | 509 | 17.65% | HIGH | Multiple chargebacks on same txn may indicate double-dispute; review. |
| Exact duplicate chargeback rows | 84 | 2.91% | MEDIUM | Remove exact duplicates in cleaning. |
| Blank txn_id in chargebacks | 81 | 2.81% | LOW | Chargebacks without txn_id cannot be linked to transactions; flag for manual review. |
| Disputed amount — blank | 183 | 6.35% | HIGH | Blank disputed amount makes financial impact assessment impossible. |
| Disputed amount — malformed | 0 | 0.00% | LOW | Strip symbols and parse to float. |
| Disputed amount — negative | 231 | 8.01% | MEDIUM | Negative disputed amounts need verification. |
| Inconsistent reason_code variants (34 raw → 33 normalised) | 2565 | 88.94% | MEDIUM | Standardise reason_code to canonical uppercase vocabulary. |
| Inconsistent resolution_status variants (13 raw → 9 normalised) | 1353 | 46.91% | MEDIUM | Standardise resolution_status to canonical uppercase vocabulary. |
| Inconsistent severity variants (16 raw → 12 normalised) | 698 | 24.20% | MEDIUM | Standardise severity to canonical uppercase vocabulary. |
| Inconsistent channel variants (8 raw → 6 normalised) | 2155 | 74.72% | MEDIUM | Standardise channel to canonical uppercase vocabulary. |
| transaction_timestamp — unix_epoch | 233 | 8.08% | HIGH | Convert Unix epoch to ISO-8601. |
| transaction_timestamp — blank | 235 | 8.15% | HIGH | Missing timestamps break dispute delay analysis. |
| reported_timestamp — unix_epoch | 237 | 8.22% | HIGH | Convert Unix epoch to ISO-8601. |
| reported_timestamp — blank | 209 | 7.25% | HIGH | Missing timestamps break dispute delay analysis. |
| bank_response_timestamp — unix_epoch | 155 | 5.37% | HIGH | Convert Unix epoch to ISO-8601. |
| bank_response_timestamp — blank | 718 | 24.90% | HIGH | Missing timestamps break dispute delay analysis. |

### Severity Distribution

| Severity Value | Count |
| --- | --- |
| P3 | 272 |
| MEDIUM | 268 |
| M | 261 |
| Medium | 254 |
| LOW | 250 |
| P4 | 249 |
| L | 248 |
| Low | 241 |
| P2 | 167 |
| H | 158 |
| High | 151 |
| HIGH | 146 |
| P1 | 65 |
| CRIT | 62 |
| Critical | 52 |
| CRITICAL | 40 |

## Referential Integrity

| Issue | Count | Percentage | Severity | Recommended Action |
| --- | --- | --- | --- | --- |
| Transaction user_id not found in KYC (normalised) | 13783 | 67.56% | CRITICAL | Normalise user_id format and re-attempt join before flagging as orphan. |
| Transaction merchant_id not found in Merchant master (normalised) | 10591 | 51.92% | HIGH | Normalise merchant_id format; orphan transactions cannot be risk-scored. |
| Chargeback txn_id not found in Transactions (normalised) | 120 | 4.16% | MEDIUM | Normalise txn_id; unlinked chargebacks cannot contribute to dispute ratio. |
| Chargeback user_id not found in KYC (normalised) | 1968 | 68.24% | HIGH | Normalise user_id; unlinked chargebacks cannot be attributed to a KYC profile. |
| Chargeback merchant_id not found in Merchant master (normalised) | 1548 | 53.68% | HIGH | Normalise merchant_id; unlinked chargebacks inflate unattributed dispute count. |

## Critical Data Risks

The following risk factors could materially affect downstream analytics if not addressed before the cleaning phase:

- **[HIGH]** Duplicate transaction IDs (txn_id): 800 records (3.92%)
- **[HIGH]** Amount — negative: 429 records (2.10%)
- **[HIGH]** Timestamp — unix_epoch: 1012 records (4.96%)
- **[CRITICAL]** Duplicate user IDs (normalised): 13768 records (37.82%)
- **[HIGH]** Malformed monthly income (unparseable after symbol strip): 1790 records (4.92%)
- **[CRITICAL]** Duplicate merchant IDs (normalised): 3279 records (52.80%)
- **[HIGH]** MCC format — unusual: 771 records (12.42%)
- **[HIGH]** Blank or invalid settlement account: 2451 records (39.47%)
- **[HIGH]** Ticket size — negative: 501 records (8.07%)
- **[CRITICAL]** Duplicate complaint IDs: 168 records (5.83%)
- **[HIGH]** Duplicate txn_id in chargebacks: 509 records (17.65%)
- **[HIGH]** Disputed amount — blank: 183 records (6.35%)
- **[HIGH]** transaction_timestamp — unix_epoch: 233 records (8.08%)
- **[HIGH]** transaction_timestamp — blank: 235 records (8.15%)
- **[HIGH]** reported_timestamp — unix_epoch: 237 records (8.22%)
- **[HIGH]** reported_timestamp — blank: 209 records (7.25%)
- **[HIGH]** bank_response_timestamp — unix_epoch: 155 records (5.37%)
- **[HIGH]** bank_response_timestamp — blank: 718 records (24.90%)
- **[CRITICAL]** Transaction user_id not found in KYC (normalised): 13783 records (67.56%)
- **[HIGH]** Transaction merchant_id not found in Merchant master (normalised): 10591 records (51.92%)
- **[HIGH]** Chargeback user_id not found in KYC (normalised): 1968 records (68.24%)
- **[HIGH]** Chargeback merchant_id not found in Merchant master (normalised): 1548 records (53.68%)

## Recommended Cleaning Actions

These actions are recommended for Milestone 2 (Cleaning). **Do not apply any changes to raw files.**

### CRITICAL Priority

1. **Duplicate user IDs (normalised)** — Normalise user_id format and deduplicate; merge or flag duplicates.
1. **Duplicate merchant IDs (normalised)** — Normalise merchant_id format and deduplicate; retain most recent record.
1. **Duplicate complaint IDs** — Investigate duplicate complaint IDs; may indicate system re-submission.
1. **Transaction user_id not found in KYC (normalised)** — Normalise user_id format and re-attempt join before flagging as orphan.

### HIGH Priority

1. **Duplicate transaction IDs (txn_id)** — Investigate duplicates; during cleaning retain the earliest record or flag all as a ring-pattern if amounts differ.
1. **Amount — negative** — Negative amounts may represent reversals; flag and verify with status.
1. **Timestamp — unix_epoch** — Convert Unix epoch timestamps to ISO-8601 datetime in cleaning.
1. **Malformed monthly income (unparseable after symbol strip)** — Manually review unparseable incomes; quarantine if unrecoverable.
1. **MCC format — unusual** — Map non-standard MCC formats to 4-digit standard.
1. **Blank or invalid settlement account** — Missing settlement account blocks payment; flag as HIGH risk.
1. **Ticket size — negative** — Negative ticket sizes are invalid; verify or quarantine.
1. **Duplicate txn_id in chargebacks** — Multiple chargebacks on same txn may indicate double-dispute; review.
1. **Disputed amount — blank** — Blank disputed amount makes financial impact assessment impossible.
1. **transaction_timestamp — unix_epoch** — Convert Unix epoch to ISO-8601.
1. **transaction_timestamp — blank** — Missing timestamps break dispute delay analysis.
1. **reported_timestamp — unix_epoch** — Convert Unix epoch to ISO-8601.
1. **reported_timestamp — blank** — Missing timestamps break dispute delay analysis.
1. **bank_response_timestamp — unix_epoch** — Convert Unix epoch to ISO-8601.
1. **bank_response_timestamp — blank** — Missing timestamps break dispute delay analysis.
1. **Transaction merchant_id not found in Merchant master (normalised)** — Normalise merchant_id format; orphan transactions cannot be risk-scored.
1. **Chargeback user_id not found in KYC (normalised)** — Normalise user_id; unlinked chargebacks cannot be attributed to a KYC profile.
1. **Chargeback merchant_id not found in Merchant master (normalised)** — Normalise merchant_id; unlinked chargebacks inflate unattributed dispute count.

### MEDIUM Priority

1. **Exact duplicate transaction rows** — Deduplicate exact rows in cleaning phase; keep one copy.
1. **Blank utr** — Records with blank utr cannot be joined or traced. Flag for quarantine review in Milestone 2.
1. **MCC with leading zero (5-digit)** — Strip leading zero to standardise to 4-digit MCC.
1. **Exact duplicate KYC rows** — Remove exact duplicate rows in cleaning.
1. **Blank pan** — Missing pan is a KYC compliance risk; flag records for manual review.
1. **Blank aadhaar** — Missing aadhaar is a KYC compliance risk; flag records for manual review.
1. **Blank date_of_birth** — Missing date_of_birth is a KYC compliance risk; flag records for manual review.
1. **Blank monthly_income** — Missing monthly_income is a KYC compliance risk; flag records for manual review.
1. **Blank signup_timestamp** — Missing signup_timestamp is a KYC compliance risk; flag records for manual review.
1. **Inconsistent KYC status casing (16 raw variants → 13 normalised)** — Normalise kyc_status to uppercase canonical values (e.g., VERIFIED, PENDING, REJECTED).
1. **Inconsistent risk_segment casing (12 raw variants)** — Normalise risk_segment to uppercase (HIGH, MEDIUM, LOW).
1. **Monthly income with currency symbol / k-suffix** — Strip ₹, INR, Rs. and expand 'k' suffix; store as numeric.
1. **Exact duplicate merchant rows** — Remove exact duplicate rows.
1. **Blank MCC code** — MCC is required for regulatory category mapping; impute from merchant_category if possible.
1. **MCC format — dashed_prefix** — Strip 'MCC-' prefix; retain 4-digit code.
1. **MCC format — leading_zero** — Strip leading zero from 5-digit MCC.
1. **Missing onboarding date** — Onboarding date is required for merchant age analysis; flag for manual lookup.
1. **Inconsistent merchant_category variants (82 raw → 44 normalised)** — Standardise merchant_category to a controlled vocabulary.
1. **Inconsistent merchant_status variants (15 raw → 12 normalised)** — Standardise merchant_status to a controlled vocabulary.
1. **Inconsistent business_type variants (14 raw → 8 normalised)** — Standardise business_type to a controlled vocabulary.
1. **Exact duplicate chargeback rows** — Remove exact duplicates in cleaning.
1. **Disputed amount — negative** — Negative disputed amounts need verification.
1. **Inconsistent reason_code variants (34 raw → 33 normalised)** — Standardise reason_code to canonical uppercase vocabulary.
1. **Inconsistent resolution_status variants (13 raw → 9 normalised)** — Standardise resolution_status to canonical uppercase vocabulary.
1. **Inconsistent severity variants (16 raw → 12 normalised)** — Standardise severity to canonical uppercase vocabulary.
1. **Inconsistent channel variants (8 raw → 6 normalised)** — Standardise channel to canonical uppercase vocabulary.
1. **Chargeback txn_id not found in Transactions (normalised)** — Normalise txn_id; unlinked chargebacks cannot contribute to dispute ratio.

### LOW Priority

1. **City capitalisation inconsistencies** — Title-case city during cleaning.
1. **Blank txn_id in chargebacks** — Chargebacks without txn_id cannot be linked to transactions; flag for manual review.

---
_FinGuard Milestone 1 — Audit Only. No records were modified or deleted._