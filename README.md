# FinGuard — UPI Fraud Ring & Merchant Risk Intelligence

## Milestone 1: Data Audit / Data Quality Engine

FinGuard is a production-quality data quality and fraud risk intelligence system built for the TransOrg AgentIQ Datathon. This milestone implements an **audit-only** data quality engine over four raw datasets: UPI transactions, KYC records, merchant master data, and chargeback complaints.

---

## Project Structure

```
FinGuard/
├── data/
│   ├── raw/          # Raw input files (read-only, never modified)
│   ├── processed/    # Cleaned / transformed data (future milestones)
│   └── quarantine/   # Records flagged during cleaning (future milestones)
├── reports/          # Generated data quality reports (JSON + Markdown)
├── src/
│   ├── ingestion/    # Data loaders for each source
│   └── quality/      # Audit engine and report generator
├── tests/            # Pytest test suite
└── notebooks/        # Exploratory notebooks (future milestones)
```

---

## Design Principles

### Raw Data is Immutable
All four source files are treated as **read-only**. No loader, audit function, or test modifies anything inside `data/raw/`. The audit engine reads the data into memory and reports findings without touching the source.

### Audit Before Cleaning
Milestone 1 performs a **comprehensive audit pass only**. No values are corrected, imputed, or removed. Cleaning decisions are deferred to Milestone 2, informed by the findings in `reports/data_quality_report.md`.

### No Silent Record Deletion
Records are **never silently dropped**. Every anomalous record is counted, categorised, and surfaced in the report. If a record is later deemed uncleanable, it will be moved to `data/quarantine/` with a logged reason — not silently discarded.

### Questionable Records are Flagged, Not Deleted
In future milestones, records that cannot be cleaned to a usable standard will be **flagged with an explicit reason code** and moved to `data/quarantine/`. They remain auditable and traceable throughout the pipeline.

### Explainable Risk Intelligence
FinGuard does not attach fraud labels to records without evidence. Every risk signal reported by the system is derived from observable data quality issues (missing IDs, duplicate keys, referential integrity failures, anomalous amounts). The system aims for **explainable risk intelligence**, not unsupported fraud claims.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full audit
python -m src.quality.audit

# Run tests
pytest tests/ -v
```

---

## Datasets

| File | Description |
|---|---|
| `track1_upi_transactions.csv` | Core UPI transaction logs |
| `track1_kyc_records.csv` | Customer KYC master data |
| `track1_merchants_master.csv` | Merchant master data |
| `track1_chargebacks.json` | Customer dispute and chargeback complaints |

Expected join keys:
- Transactions ↔ KYC: `user_id`
- Transactions ↔ Merchants: `merchant_id`
- Chargebacks ↔ Transactions: `txn_id`
- Chargebacks ↔ KYC: `user_id`
- Chargebacks ↔ Merchants: `merchant_id`

---

## Output

After running the audit, two reports are generated in `reports/`:

- `data_quality_report.json` — machine-readable full audit results
- `data_quality_report.md` — human-readable executive summary with severity-tagged issues and recommended cleaning actions

---

## Note

All data is synthetic, generated for educational and datathon purposes only. No real customer, merchant, or financial data is used.
