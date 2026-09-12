# FinGuard — UPI Fraud Ring & Merchant Risk Intelligence

## Project Overview

FinGuard is a production-quality data quality and fraud risk intelligence system built for the TransOrg AgentIQ Datathon. It processes UPI transactions, KYC records, merchant master data, and chargeback complaints through a rigorous multi-stage pipeline.

---

## Project Structure

```
FinGuard/
├── data/
│   ├── raw/               # Raw input files (read-only, never modified)
│   ├── processed/         # Cleaned / integrated analytics-ready datasets
│   └── quarantine/        # Records flagged during cleaning
├── reports/               # Generated reports (JSON + Markdown)
├── src/
│   ├── ingestion/         # Data loaders for each source
│   ├── quality/           # Audit engine and report generator
│   ├── cleaning/          # Normalization and cleaning modules
│   └── integration/       # Unified data model builder
├── tests/                 # Pytest test suite (43 tests)
└── notebooks/             # Exploratory notebooks
```

---

## Design Principles

- **Raw Data is Immutable** — nothing inside `data/raw/` is ever touched
- **No Silent Record Deletion** — every dropped row is counted and justified
- **Flags, Not Deletion** — messy records are flagged with reason codes, never blindly removed
- **Explainable Risk Intelligence** — every risk signal is derived from observable data quality issues
- **Full Traceability** — `source_dataset` and `source_row_number` preserved end-to-end

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Milestone 1: Run the data quality audit
python -m src.quality.audit

# Milestone 2: Run the cleaning & normalization pipeline
python -m src.cleaning.pipeline

# Milestone 2 (Validation): Run join diagnostics
python -m src.cleaning.diagnostics

# Milestone 3: Build the unified data model
python -m src.integration.build_model

# Run all tests (43 tests, Milestones 1-3)
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

---

## Milestone 1: Data Audit / Data Quality Engine

Performs a **comprehensive read-only audit** of all four raw datasets. No values are corrected or removed.

**Outputs:**
- `reports/data_quality_report.json`
- `reports/data_quality_report.md`

---

## Milestone 2: Data Cleaning & Normalization

Transforms raw data into analytics-ready form while preserving full traceability.

| Transformation | Description |
|---|---|
| ID Normalization | `USR-12345`, `usr12345`, `12345` → `USR12345` (symmetric, deterministic) |
| Amount Cleaning | Strips currency symbols; flags negative/zero/failed/missing |
| Timestamp Normalization | ISO, slash, AM/PM, Unix epoch; generates `_clean`, `_missing`, `_parse_failed`, `_was_epoch` |
| Status Canonicalization | `S` / `TXN_SUCCESS` / `Success` → `SUCCESS` |
| MCC Normalization | `05411` / `MCC-5411` → `5411` as 4-character string |
| UTR Cleaning | Strips whitespace and hyphens; flags missing/invalid |
| Duplicate Handling | Exact duplicates removed; ID duplicates flagged, retained |
| Referential Integrity | `user_fk_missing`, `merchant_fk_missing`, `chargeback_txn_fk_missing` flags |

**Outputs:** `data/processed/*_clean.csv`, `reports/cleaning_report.md`, `reports/post_cleaning_validation.md`

---

## Milestone 3: Unified Data Model

### Pipeline: RAW → CLEAN → VALIDATED → INTEGRATED

```
data/raw/                                    (immutable)
    ↓ src/ingestion/loaders.py
data/processed/*_clean.csv                   (Milestone 2: normalized)
    ↓ src/cleaning/diagnostics.py
reports/post_cleaning_validation.md          (join diagnostics)
    ↓ src/integration/build_model.py
data/processed/finguard_transactions.csv     (unified fact table, 20,000 rows conserved)
data/processed/users_analytics.csv          (one row per user)
data/processed/merchants_analytics.csv      (one row per merchant)
data/processed/chargebacks_aggregated.csv   (one row per transaction)
reports/integration_report.md
```

### Entity Resolution Strategy

| Entity | Strategy |
|---|---|
| KYC (user) | Most complete record; ties broken by most recent `signup_timestamp_clean` |
| Merchants | Most complete record; ties broken by most recent `onboarding_date_clean` |
| Chargebacks | Aggregated per `txn_id` — no transaction row duplication |

### Key Metrics

| Metric | Formula |
|---|---|
| `chargeback_rate` | `chargeback_count / transaction_count` |
| `disputed_amount_ratio` | `total_disputed_amount / total_transaction_amount` |
| `success_rate` | `successful_transaction_count / transaction_count` |
| `failure_rate` | `failed_transaction_count / transaction_count` |

All metrics handle division by zero safely (result = 0).

---

## Note

All data is synthetic, generated for educational and datathon purposes only. No real customer, merchant, or financial data is used.
