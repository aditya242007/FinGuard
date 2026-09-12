# Walkthrough – FinGuard Milestone 4.1 (Comprehensive EDA & KPI Baseline)

**Executed script:** `src/eda/m4_eda.py`

**Key actions performed:**
- Loaded processed datasets (`finguard_transactions.csv`, `users_analytics.csv`, `merchants_analytics.csv`, `chargebacks_aggregated.csv`).
- Cast numeric columns, parsed timestamps, and coerced boolean flags.
- Computed transaction KPIs (counts, amounts, success/failure rates, daily averages).
- Computed chargeback KPIs (rate, disputed amount ratios, delay metrics).
- Computed data‑quality KPIs (UTR missing, negative amounts, invalid timestamps, unmatched KYC/merchant, duplicate TXN IDs, referential integrity issues).
- Added outlier flags (IQR and Z‑score based) to the transaction dataframe.
- Generated 15 high‑quality visualisations saved under `reports/figures/m4/`.
- Produced markdown and JSON KPI reports (`reports/m4_kpi_baseline.json`, `reports/m4_kpi_baseline.csv`).
- Generated a detailed EDA report (`reports/m4_eda_report.md`) containing KPI tables, top categories/merchants, chargeback analyses, and data‑quality summaries.
- Ran validation checks – all passed (`txn_count_equals_20000`, `status_rates_sum_le100`, etc.).

**Outputs created:**
- `reports/figures/m4/*.png` (15 charts)
- `reports/m4_kpi_baseline.json`
- `reports/m4_kpi_baseline.csv`
- `reports/m4_insights.md`
- `reports/m4_eda_report.md`

All tests now pass (`49 passed`). The EDA pipeline is ready for review.  

*Next steps (if desired):* further business KPI deep‑dives, dashboard creation, or model development.
