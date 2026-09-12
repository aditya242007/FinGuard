# FinGuard M5 Feature Validation

## 1. Feature Generation Overview
- **Transaction Features**: 34
- **User Features**: 24
- **Merchant Features**: 26
- **Chargeback Features**: 7

## 2. Row Counts
- **transaction_risk_features.csv**: 20,000 (Matches M3 source exactly, no join explosion)
- **user_risk_features.csv**: 17,878 (Unique normalized user IDs)
- **merchant_risk_features.csv**: 8,051 (Unique normalized merchant IDs)
- **chargeback_risk_features.csv**: 2,567 (Matches expected chargeback grain)

## 3. Top Candidate Risk Signals
1. `chargeback_rate` (User & Merchant) - Direct proxy for historical dispute ratio.
2. `disputed_amount_ratio` (Merchant) - Exposes high financial risk relative to total volume.
3. `user_relative_amount_anomaly` (Transaction) - Identifies behavioral spikes for an individual user.
4. `amount_iqr_anomaly_flag` (Transaction) - Flags extreme global outliers.
5. `failure_rate` (User & Merchant) - High failure frequencies may indicate credential testing.
6. `dispute_after_7_days_rate` (User & Merchant) - Identifies merchants processing late-reported or delayed-discovery fraud patterns.
7. `missing_utr_flag` (Transaction) - Indicates broken payment reconciliation logic which correlates strongly with high-risk platforms.
8. `kyc_duplicate_entity_flag` (User) - Multiple users linked to the same KYC details.
9. `negative_amount_flag` (Transaction) - Captures potentially anomalous reversal behavior without removing the data point.
10. `timestamp_invalid_flag` (Transaction) - Flags system-level data quality manipulations.

## 4. Leakage Risks
All chargeback metrics (e.g. `has_chargeback`, `chargeback_rate`) are labeled strictly as **POST-EVENT (RETROSPECTIVE)**. Using these as predictors at transaction-time in M6 will guarantee temporal leakage and over-optimistic model performance. Aggregated features (like total volume) are currently calculated globally rather than using point-in-time constraints.

## 5. Negative Value & Missingness Handling
- **Negative Values**: Fully preserved across all tables (e.g. `amount_numeric`, `total_transaction_amount`), generating accurate net calculations without silent positive conversions.
- **Missingness & Small N Rules**: 
  - Standard deviations and z-scores dynamically return `NaN` when $N < 5$, preventing misleading zero-variance infinities.
  - Rate calculation denominators (e.g., `transaction_count`) are protected using safe division mapping zeros to standard behavior.

## 6. Testing Results
- Pytest verified row-count consistency, deterministic logic, absence of `inf` values, and preservation of negative data attributes.
