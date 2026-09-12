# M8 Dashboard Validation Report

## Architecture & Technology
The M8 FinGuard Risk Intelligence Dashboard was built using:
- **Framework:** React + TypeScript via Vite
- **Styling:** Tailwind CSS (v4)
- **Charts:** Recharts
- **State Management:** Zustand
- **Data Loading:** PapaParse for client-side CSV processing.

The dashboard runs locally and processes the static authoritative datasets from M4-M7 by loading them directly into memory for high-performance filtering.

## Pages Implemented
1. **`/` (Executive Overview):** Top-level KPIs, data quality panel, and volume trends.
2. **`/risk` (Fraud & Risk Intelligence):** Tables for top risk entities (Merchants, Suspicious Clusters).
3. **`/merchants` (Merchant Intelligence):** Charts analyzing merchant transaction volume and chargeback rates by category.
4. **`/investigate` (Investigation Explorer):** Global search mechanism to inspect a Cluster or Transaction and view explainable risk signals.

## Datasets Consumed
All datasets are synced to `dashboard/public/data/` via `scripts/prepare_dashboard_data.py`:
- `finguard_transactions.csv` (20,000 records)
- `users_analytics.csv` & `user_risk_scores.csv`
- `merchants_analytics.csv` & `merchant_risk_scores.csv`
- `suspicious_clusters.csv` (655 clusters)

## Validation Results
All 8 automated tests passed (`tests/test_m8_dashboard_data.py`), confirming:
1. `finguard_transactions.csv` count is exactly 20,000.
2. Max chargeback rate in the cluster outputs is <= 1.0.
3. CLU00604 shows exactly 100% (1.0) chargeback rate and preserves the 2 raw complaint records.
4. No fabricated IDs were introduced.
5. Merchant risk levels only contain LOW, MEDIUM, HIGH, CRITICAL.
6. No NaN/Infinity display issues in cluster scores.

## Known Limitations
- **Data Scale:** The dashboard relies on loading all data into client browser memory. This is highly performant for 20,000 transactions but will require a proper API backend (e.g., FastAPI + PostgreSQL) if the dataset grows to millions of rows.
- **Investigation Explorer:** The current search is exact-match and heavily simplified for demonstration. 
- **Graph Visualization:** A node/edge graph library (e.g. Cytoscape) was omitted to avoid excessive frontend complexity, relying instead on tabular breakdowns of the cluster components.
