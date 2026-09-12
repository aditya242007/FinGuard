# M8 Dashboard Data Contract

## Overview
This document outlines the data contract between the FinGuard processed data layer (M0-M7) and the M8 FinGuard Risk Intelligence Dashboard.

## Core Datasets Consumed

### 1. `transaction_risk_scores.csv` & `transaction_risk_features.csv`
- **Primary Key:** `txn_id_normalized` (or `txn_id`)
- **Important Dimensions:** `transaction_date`, `transaction_hour`, `success_flag`, `failed_flag`, `transaction_time_risk_level`, `retrospective_risk_level`, `top_risk_signal_1...3`, `explanation`
- **Important Metrics:** `amount_abs`, `transaction_time_risk_score`, `retrospective_risk_score`
- **Relationships:** Links to Users (`user_id_normalized`), Merchants (`merchant_id_normalized`), Chargebacks.

### 2. `user_risk_scores.csv` & `users_analytics.csv` / `user_risk_features.csv`
- **Primary Key:** `user_id_normalized` (or `user_id`)
- **Important Dimensions:** `risk_level`, `kyc_status_clean`, `kyc_match_flag`, `top_risk_signal_1...3`, `explanation`
- **Important Metrics:** `retrospective_risk_score`, `transaction_count`, `total_transaction_amount`, `chargeback_rate`, `total_disputed_amount`, `success_rate`, `failure_rate`
- **Relationships:** 1:N with Transactions.

### 3. `merchant_risk_scores.csv` & `merchants_analytics.csv` / `merchant_risk_features.csv`
- **Primary Key:** `merchant_id_normalized` (or `merchant_id`)
- **Important Dimensions:** `risk_level`, `merchant_category`, `merchant_status`, `top_risk_signal_1...3`, `explanation`
- **Important Metrics:** `retrospective_risk_score`, `transaction_count`, `total_transaction_amount`, `chargeback_rate`, `disputed_amount_ratio`, `success_rate`, `failure_rate`
- **Relationships:** 1:N with Transactions.

### 4. `suspicious_clusters.csv`
- **Primary Key:** `cluster_id`
- **Important Dimensions:** `risk_level`, `top_signals`, `explanation`
- **Important Metrics:** `cluster_risk_score`, `n_users`, `n_merchants`, `n_transactions`, `chargeback_count`, `chargebacked_transaction_count`, `cluster_chargeback_rate`, `disputed_amount`, `disputed_amount_ratio`
- **Relationships:** Represents components of a graph containing Users, Merchants, Transactions, and Chargebacks.

### 5. `finguard_transactions.csv` (Base Master)
- **Primary Key:** `txn_id_normalized`
- **Important Dimensions:** `status_clean`, `kyc_status_clean`, `merchant_category_clean`
- **Important Metrics:** `amount_numeric`, `chargeback_count`, `total_disputed_amount`
- **Known Limitations:** Missing UTRs, missing KYC, missing merchant data, negative transaction amounts, referential integrity issues.

## Metric Definitions
- **Chargeback Rate (Users/Merchants/Clusters):** Count of distinct transactions with >= 1 chargeback divided by total transaction count. Always in `[0, 1]`.
- **Disputed Amount Ratio:** Total disputed amount divided by total transaction amount. Can exceed 1.0.
- **Transaction-Time Risk Score:** Computed based solely on data available at the time of the transaction (no future leakage).
- **Retrospective Risk Score:** Computed using aggregated historical data across the entire dataset timeframe.

## Data Quality Limitations (Must NOT be hidden)
- **Unmatched KYC & Merchants:** A significant portion of transactions lack valid KYC or Merchant entities.
- **Missing UTRs:** Indicates potential data extraction or settlement traceability issues.
- **Negative Amounts:** Represent data-quality anomalies or refunds/reversals, not necessarily fraudulent behavior.
- **"Fraud" Labels:** The dataset does NOT contain ground-truth fraud labels. All scores represent **risk/behavioral anomalies**, not confirmed fraud.

## Semantics
- Use **"Risk Level"**, **"Suspicious Cluster"**, **"Investigation Candidate"**.
- Do NOT use "Fraudulent User" or "Confirmed Fraud".
