# FinGuard — Master Judge & Evaluator Guide
### TransOrg AgentIQ Datathon — Track 1: FinTech & BFSI (UPI Fraud Ring & Merchant Risk Intelligence)

[![Pytest Suite](https://img.shields.io/badge/pytest-241%20passed%20%7C%20100%25-brightgreen)](tests/)
[![Data Conservation](https://img.shields.io/badge/Row%20Conservation-20%2C000%2F20%2C000%20(100%25)-blue)](data/processed/finguard_transactions.csv)
[![Dashboard](https://img.shields.io/badge/Dashboard-React%2018%20%2B%20TypeScript%20%2B%20Vite-purple)](dashboard/)
[![AI Copilot](https://img.shields.io/badge/AI%20Copilot-Google%20Gemini%20%2B%20SafetyGuard-orange)](src/m9_agent/)
[![Architecture](https://img.shields.io/badge/Architecture-End--to--End%20M1--M10-darkgreen)](reports/)

> **Welcome Judges!**  
> This master document is designed to give you an **immediate, comprehensive, and in-depth understanding** of the FinGuard platform without overwhelming you. It explains the core architecture, every data process step-by-step, exact file paths, full statistical insights, all 15 visual chart figures, and complete reproducibility commands.

---

## Table of Contents

1. [Executive Summary (3-Minute Read)](#1-executive-summary-3-minute-read)
2. [Master File Index — Where to Find What](#2-master-file-index--where-to-find-what)
3. [Architecture & Design Governance](#3-architecture--design-governance)
4. [Step-by-Step Pipeline Walkthrough (M1 – M10)](#4-step-by-step-pipeline-walkthrough-m1--m10)
5. [Visual Chart Gallery & Analytical Deep Dive (15 Figures)](#5-visual-chart-gallery--analytical-deep-dive-15-figures)
6. [Core Business Insights & Financial Metrics](#6-core-business-insights--financial-metrics)
7. [Explainable Risk Scoring Methodology](#7-explainable-risk-scoring-methodology)
8. [Graph Intelligence & Fraud Ring Detection](#8-graph-intelligence--fraud-ring-detection)
9. [Executive Investigation Dashboard](#9-executive-investigation-dashboard)
10. [Autonomous AI Copilot & Safety Guardrails](#10-autonomous-ai-copilot--safety-guardrails)
11. [How to Run & Reproduce (Quickstart)](#11-how-to-run--reproduce-quickstart)
12. [Verification & Test Results Summary](#12-verification--test-results-summary)

---

## 1. Executive Summary (3-Minute Read)

FinGuard is a production-grade **UPI Fraud Ring & Merchant Risk Intelligence Platform** built for high-throughput digital payments. The system ingests messy, disparate financial logs and turns them into an explainable, graph-powered investigation engine and executive intelligence suite.

```
RAW DATA STREAMS               DATA REFINERY                 INTELLIGENCE LAYER           INTERFACES
┌─────────────────────────┐   ┌───────────────────────────┐   ┌────────────────────────┐   ┌──────────────────────────┐
│ track1_upi_txns.csv     │──>│ M1: Read-Only Audit Engine│──>│ M5: Point-in-Time Store│──>│ M8: Executive Dashboard  │
│ track1_kyc_records.csv  │   │ M2: Zero-Loss Cleaning    │   │ M6: Explainable Risk   │   │     (React/TS/Tailwind)  │
│ track1_merchants.csv    │   │ M3: Star-Schema Model     │   │ M7: Graph & Ring Detect│   ├──────────────────────────┤
│ track1_chargebacks.json │   │ M4: Visual EDA (15 Charts)│   │ M10: Safety Guardrails │──>│ M9: Gemini AI Copilot   │
└─────────────────────────┘   └───────────────────────────┘   └────────────────────────┘   └──────────────────────────┘
```

### Key Highlights for Evaluators:
- **100% Row Conservation (Zero Silent Deletions)**: All 20,000 raw transactions are preserved in the unified model (`finguard_transactions.csv`). Anomalous, negative, or missing-UTR records are tagged with diagnostic reason codes rather than silently dropped.
- **Strict Leakage Prevention**: Enforces a strict separation between **Mode A (Transaction-Time Risk)** using only point-in-time expanding windows, and **Mode B (Retrospective Investigation)** utilizing historical dispute outcomes.
- **Bipartite Graph Network**: Constructs a 25,929-node NetworkX bipartite graph (17,878 users, 8,051 merchants) with Louvain community detection and dense cluster analysis (`suspicious_clusters.csv`).
- **Full Test Coverage**: **241 passed automated tests** covering every ingestion, transformation, risk calculation, graph algorithm, safety guardrail, and data contract.
- **Enterprise Safety Guardrails**: Prevents defamatory LLM claims without ground-truth labels, enforces regulatory disclaimers, and sanitizes PII.

---

## 2. Master File Index — Where to Find What

Use this index to quickly locate any file, dataset, report, or test in the repository:

| Milestone / Area | Exact Source Code Path | Key Output / Data Artifact | Primary Report / Documentation | Verification Tests |
|---|---|---|---|---|
| **M1: Data Quality Audit** | [`src/quality/audit.py`](src/quality/audit.py)<br>[`src/ingestion/loaders.py`](src/ingestion/loaders.py) | Raw input profiling (read-only) | [`reports/data_quality_report.md`](reports/data_quality_report.md)<br>[`reports/data_quality_report.json`](reports/data_quality_report.json) | [`tests/test_audit.py`](tests/test_audit.py) |
| **M2: Cleaning & Quarantine** | [`src/cleaning/pipeline.py`](src/cleaning/pipeline.py)<br>[`src/cleaning/ids.py`](src/cleaning/ids.py)<br>[`src/cleaning/timestamps.py`](src/cleaning/timestamps.py)<br>[`src/cleaning/amounts.py`](src/cleaning/amounts.py) | [`data/processed/transactions_clean.csv`](data/processed/transactions_clean.csv)<br>[`data/processed/kyc_clean.csv`](data/processed/kyc_clean.csv)<br>[`data/processed/merchants_clean.csv`](data/processed/merchants_clean.csv)<br>[`data/processed/chargebacks_clean.csv`](data/processed/chargebacks_clean.csv) | [`reports/cleaning_report.md`](reports/cleaning_report.md)<br>[`reports/post_cleaning_validation.md`](reports/post_cleaning_validation.md) | [`tests/test_cleaning.py`](tests/test_cleaning.py) |
| **M3: Unified Data Model** | [`src/integration/build_model.py`](src/integration/build_model.py)<br>[`src/cleaning/diagnostics.py`](src/cleaning/diagnostics.py) | [`data/processed/finguard_transactions.csv`](data/processed/finguard_transactions.csv)<br>[`data/processed/users_analytics.csv`](data/processed/users_analytics.csv)<br>[`data/processed/merchants_analytics.csv`](data/processed/merchants_analytics.csv)<br>[`data/processed/chargebacks_aggregated.csv`](data/processed/chargebacks_aggregated.csv) | [`reports/integration_report.md`](reports/integration_report.md)<br>[`reports/m3_join_reconciliation.md`](reports/m3_join_reconciliation.md) | [`tests/test_integration.py`](tests/test_integration.py) |
| **M4: EDA & Chart Suite** | [`src/eda/generate_figures.py`](src/eda/generate_figures.py)<br>[`src/eda/generate_kpis.py`](src/eda/generate_kpis.py) | 15 PNG figures in [`reports/figures/m4/`](reports/figures/m4/)<br>[`reports/m4_kpi_baseline.json`](reports/m4_kpi_baseline.json) | [`reports/m4_eda_report.md`](reports/m4_eda_report.md)<br>[`reports/m4_insights.md`](reports/m4_insights.md) | Baseline KPI assertions |
| **M5: Feature Store** | [`src/features/build_features.py`](src/features/build_features.py) | [`data/processed/features/transaction_risk_features.csv`](data/processed/features/transaction_risk_features.csv)<br>[`data/processed/features/user_risk_features.csv`](data/processed/features/user_risk_features.csv)<br>[`data/processed/features/merchant_risk_features.csv`](data/processed/features/merchant_risk_features.csv) | [`reports/m5_feature_dictionary.md`](reports/m5_feature_dictionary.md)<br>[`reports/m5_feature_validation.md`](reports/m5_feature_validation.md) | [`tests/test_m5_features.py`](tests/test_m5_features.py) |
| **M6: Risk Scoring Engine** | [`src/risk/engine.py`](src/risk/engine.py) | [`data/processed/risk/transaction_risk_scores.csv`](data/processed/risk/transaction_risk_scores.csv)<br>[`data/processed/risk/user_risk_scores.csv`](data/processed/risk/user_risk_scores.csv)<br>[`data/processed/risk/merchant_risk_scores.csv`](data/processed/risk/merchant_risk_scores.csv) | [`reports/m6_risk_methodology.md`](reports/m6_risk_methodology.md)<br>[`reports/m6_risk_engine_validation.md`](reports/m6_risk_engine_validation.md) | [`tests/test_m6_risk_engine.py`](tests/test_m6_risk_engine.py) |
| **M7: Graph & Ring Detection** | [`src/risk/graph_engine.py`](src/risk/graph_engine.py) | [`data/processed/graph/graph_nodes.csv`](data/processed/graph/graph_nodes.csv)<br>[`data/processed/graph/graph_edges.csv`](data/processed/graph/graph_edges.csv)<br>[`data/processed/graph/suspicious_clusters.csv`](data/processed/graph/suspicious_clusters.csv)<br>[`data/processed/graph/cluster_members.csv`](data/processed/graph/cluster_members.csv) | [`reports/m7_graph_methodology.md`](reports/m7_graph_methodology.md)<br>[`reports/m7_graph_validation.md`](reports/m7_graph_validation.md) | [`tests/test_m7_graph_analysis.py`](tests/test_m7_graph_analysis.py) |
| **M8: Executive Dashboard** | [`dashboard/src/App.tsx`](dashboard/src/App.tsx)<br>[`dashboard/src/pages/`](dashboard/src/pages/) | Fully compiled SPA in [`dashboard/dist/`](dashboard/dist/) | [`reports/m8_dashboard_data_contract.md`](reports/m8_dashboard_data_contract.md)<br>[`reports/m8_dashboard_validation.md`](reports/m8_dashboard_validation.md) | [`tests/test_m8_dashboard_contract.py`](tests/test_m8_dashboard_contract.py) |
| **M9: Autonomous Copilot** | [`src/m9_agent/agent.py`](src/m9_agent/agent.py)<br>[`src/m9_agent/data_tools.py`](src/m9_agent/data_tools.py)<br>[`src/m9_agent/api.py`](src/m9_agent/api.py) | Real-time tool-augmented LLM responses with audit logs | [`reports/m8_gemini_audit.md`](reports/m8_gemini_audit.md) | [`tests/test_m9_agent.py`](tests/test_m9_agent.py)<br>[`tests/test_m9_evaluation.py`](tests/test_m9_evaluation.py) |
| **M10: Safety Guardrails** | [`src/m9_agent/safety_guard.py`](src/m9_agent/safety_guard.py)<br>[`live_validation.py`](live_validation.py) | Interceptor & policy enforcement engine | [`reports/m10_1_live_validation_report.md`](reports/m10_1_live_validation_report.md) | [`tests/test_m10_2_safety_guard.py`](tests/test_m10_2_safety_guard.py) |

---

## 3. Architecture & Design Governance

FinGuard is engineered around five fundamental enterprise principles:

1. **Raw Data is Strictly Read-Only**: `data/raw/` contains raw inputs that are never mutated.
2. **Zero Silent Record Deletion**: Financial regulators and fraud investigators require full auditability. Dropping rows creates survivorship bias. FinGuard flags anomalous records with reason codes (`INVALID_AMOUNT`, `MISSING_UTR`, `UNVERIFIED_KYC`) while keeping the 20,000 transaction denominator intact.
3. **Strict Point-in-Time Integrity**: Real-time payment scoring cannot look into the future. Chargebacks arrive days or weeks later. Mode A risk scoring strictly isolates pre-transaction features using expanding windows, preventing target leakage.
4. **Deterministic & Explainable Scoring**: Every risk score (0–100) breaks down into additive sub-weights with human-readable rationale strings.
5. **Defamation & Hallucination Guardrails**: Because ground-truth criminal convictions do not exist in the dataset, the AI agent is barred from declaring an entity "guilty" or "100% fraudulent", instead outputting legally safe "elevated-risk investigation candidate" summaries.

---

## 4. Step-by-Step Pipeline Walkthrough (M1 – M10)

```
       [Raw Files]
            │
            ▼
┌───────────────────────┐
│ M1: Data Audit        │ Profiling schema, missing foreign keys, anomalous distributions
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ M2: Cleaning Pipeline │ Normalizes IDs, amounts, timestamps (ISO/Epoch/Slash), statuses, MCCs
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ M3: Unified Model     │ 20,000 txns conserved; User & Merchant entity resolution; 1:1 fact table
└───────────┬───────────┘
            │
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────┐                  ┌───────────────────────┐
│ M4: Exploratory EDA   │ 15 charts        │ M5: Feature Store     │ PIT features & historical
└───────────────────────┘                  └───────────┬───────────┘
                                                       │
                                                       ▼
                                           ┌───────────────────────┐
                                           │ M6: Risk Scoring      │ Mode A (Real-time) vs Mode B (Post-event)
                                           └───────────┬───────────┘
                                                       │
                                                       ▼
                                           ┌───────────────────────┐
                                           │ M7: Graph Analytics   │ Bipartite graph, 25k nodes, ring clusters
                                           └───────────┬───────────┘
                                                       │
                        ┌──────────────────────────────┴──────────────────────────────┐
                        ▼                                                             ▼
            ┌───────────────────────┐                                     ┌───────────────────────┐
            │ M8: React Dashboard   │ Executive visual workbench          │ M9/M10: AI Copilot    │ Gemini + Safety Guard
            └───────────────────────┘                                     └───────────────────────┘
```

### Phase 1: Data Audit & Profiling Engine (M1)
- **Objective**: Perform a comprehensive, read-only diagnostic on all four raw datasets without altering values.
- **Key Findings Identified**:
  - `track1_upi_transactions.csv`: 20,000 transactions; 1,000 missing UTRs (5.0%); 420 negative amounts (2.1%); 14 distinct timestamp formats.
  - `track1_kyc_records.csv`: 10,000 customer records; only 32.39% coverage of transaction users (67.61% transactions lack user KYC).
  - `track1_merchants_master.csv`: 5,000 merchants; 51.84% of transactions lack a matching merchant master record.
  - `track1_chargebacks.json`: 2,800 dispute records across 2,451 unique transactions (some transactions have multiple complaints).

### Phase 2: Cleaning, Normalization & Quarantine Engine (M2)
- **Objective**: Standardize messy formats, strip currency noise, parse chaotic timestamps, and resolve referential integrity.
- **Core Transformations**:
  - **ID Normalization**: Regex rules convert `USR-12345`, `usr12345`, `USR 12345`, `12345` → `USR12345`.
  - **Timestamp Normalizer**: Parses ISO 8601, slash formats (`DD/MM/YYYY` and `MM/DD/YYYY`), 12-hour AM/PM, and Unix epoch milliseconds into standardized UTC datetimes. Generates diagnostic flags (`timestamp_was_epoch`, `timestamp_parse_failed`).
  - **Amount Cleaning**: Strips currency symbols (`₹`, `$`, `Rs.`), commas, and spaces. Retains negative amounts with flag `amount_is_negative = True`.
  - **Status Canonicalization**: Normalizes `S`, `Success`, `TXN_SUCCESS`, `COMPLETED` → `SUCCESS`; `FAIL`, `Declined` → `FAILED`; `Pending`, `PROCESSING` → `PENDING`.
  - **MCC Standardization**: Formats merchant codes as 4-character strings (e.g., `05411` or `MCC-5411` → `5411`).
  - **Referential Integrity**: Computes boolean flags `user_fk_missing`, `merchant_fk_missing`, `chargeback_txn_fk_missing`.

### Phase 3: Unified Star-Schema Data Model (M3)
- **Objective**: Integrate disparate tables into a unified analytical data warehouse while conserving every record.
- **Conservation Result**: Exactly **20,000 transactions preserved** in `finguard_transactions.csv`.
- **Entity Resolution**:
  - Users: Resolved to 17,878 distinct users in `users_analytics.csv`. Ties broken by completeness score and newest signup timestamp.
  - Merchants: Resolved to 8,051 distinct merchants in `merchants_analytics.csv`.
  - Disputes: Grouped per transaction in `chargebacks_aggregated.csv` to ensure zero fan-out/multiplication of transaction rows during joins.

### Phase 4: Exploratory Data Analysis & Business Intelligence (M4)
- **Objective**: Extract core payment benchmarks, merchant velocity metrics, chargeback ratios, and seasonal patterns across 15 high-definition figures.

### Phase 5: Feature Engineering & Feature Store (M5)
- **Objective**: Compute behavioral, velocity, and risk features with zero future leakage.
- **Mode A Features (Transaction-Time)**:
  - `user_expanding_failure_rate`: Expanding failure mean using only preceding transactions (`shift(1)`).
  - `user_amount_zscore_relative`: User's deviation from their own personal historical mean.
  - `missing_utr_flag`, `invalid_timestamp_flag`, `unverified_kyc_flag`.
- **Mode B Features (Retrospective)**:
  - `merchant_chargeback_rate`, `merchant_disputed_amount_ratio`, `delayed_dispute_ratio`.

### Phase 6: Deterministic Risk Scoring Engine (M6)
- **Objective**: Score transactions, users, and merchants on a 0–100 scale with full human interpretability.
- **Risk Tiers**:
  - `LOW`: 0 – 29
  - `MEDIUM`: 30 – 59
  - `HIGH`: 60 – 79
  - `CRITICAL`: 80 – 100
- **Explainability Contract**: Every score includes a list of triggered reason codes and mathematical point contributions.

### Phase 7: Bipartite Graph Analytics & Fraud Ring Detection (M7)
- **Objective**: Detect coordinated merchant-user rings, high-density clusters, and dispute velocity spikes.
- **Graph Topology**: 25,929 nodes (17,878 Users, 8,051 Merchants) connected by 20,000 transaction edges.
- **Algorithms Applied**:
  - Connected component partitioning.
  - Louvain modularity clustering.
  - High-risk cluster filtering (`suspicious_clusters.csv`).

### Phase 8: Executive Investigation Dashboard (M8)
- **Objective**: Deliver a zero-latency, high-aesthetic analyst interface.
- **Tech Stack**: React 18, TypeScript, Tailwind CSS, Lucide icons, Vite build tool.
- **Modules**: Executive Overview, Merchant Intelligence, Risk Intelligence, Graph Ring Explorer.

### Phase 9 & 10: Autonomous AI Copilot & Safety Guardrails (M9 & M10)
- **Objective**: Enable conversational investigations through Google Gemini with deterministic tool execution and strict enterprise safety guardrails.

---

## 5. Visual Chart Gallery & Analytical Deep Dive (15 Figures)

All 15 figures below are generated by [`src/eda/generate_figures.py`](src/eda/generate_figures.py) and stored in [`reports/figures/m4/`](reports/figures/m4/).

### Figure 1: Daily Transaction Volume Trend
![Daily Transaction Count](reports/figures/m4/01_daily_txn_count.png)
- **Path**: `reports/figures/m4/01_daily_txn_count.png`
- **Insight**: Highlights daily processing volume across the observation window, identifying regular cycle stability punctuated by specific weekend dips and mid-week spikes.

---

### Figure 2: Daily Transaction Total Value (INR)
![Daily Transaction Value](reports/figures/m4/02_daily_txn_value.png)
- **Path**: `reports/figures/m4/02_daily_txn_value.png`
- **Insight**: Total daily value processed. Shows correlation with daily count, confirming ticket sizes remain stable across regular days without artificial single-day gross value distortion.

---

### Figure 3: Transaction Status Breakdown
![Transaction Status](reports/figures/m4/03_status_distribution.png)
- **Path**: `reports/figures/m4/03_status_distribution.png`
- **Insight**: **85.26% Success Rate** (17,053 transactions), **9.78% Failure Rate** (1,955 transactions), and **4.96% Pending Rate** (992 transactions). Proves baseline network reliability while establishing normal baseline failure thresholds.

---

### Figure 4: Hourly Transaction Volume Distribution
![Hourly Volume](reports/figures/m4/04_hourly_volume.png)
- **Path**: `reports/figures/m4/04_hourly_volume.png`
- **Insight**: Transaction volume peaks between **00:00 and 01:00**, indicating automated scheduled batch runs or nocturnal digital commerce activity, with daytime traffic remaining consistently distributed.

---

### Figure 5: Hourly Failure Rate Anomaly Curve
![Hourly Failure Rate](reports/figures/m4/05_hourly_failure_rate.png)
- **Path**: `reports/figures/m4/05_hourly_failure_rate.png`
- **Insight**: Failure rates spike to their daily peak at **11:00 AM**, indicating bank gateway congestion or NPCI clearing window throttles during late morning banking rush hours.

---

### Figure 6: Top Merchant Categories by Transaction Value
![Top Categories Value](reports/figures/m4/06_top_categories_value.png)
- **Path**: `reports/figures/m4/06_top_categories_value.png`
- **Insight**: Identifies leading economic categories across 44 distinct segments. Categories like Telecom, Utilities, and Electronics drive the highest aggregate INR flow.

---

### Figure 7: Top Merchants by Transaction Value
![Top Merchants Value](reports/figures/m4/07_top_merchants_value.png)
- **Path**: `reports/figures/m4/07_top_merchants_value.png`
- **Insight**: Low merchant concentration: the top 5 individual merchants represent only **0.23% (45 transactions)** of total volume, proving a highly decentralized merchant base.

---

### Figure 8: Daily Chargeback Dispute Trend
![Daily Chargebacks](reports/figures/m4/08_daily_chargebacks.png)
- **Path**: `reports/figures/m4/08_daily_chargebacks.png`
- **Insight**: Tracking daily dispute filings reveals dispute latency waves that lag transaction volume spikes by multiple business days.

---

### Figure 9: Chargeback Distribution by Category
![Chargeback by Category](reports/figures/m4/09_cb_by_category.png)
- **Path**: `reports/figures/m4/09_cb_by_category.png`
- **Insight**: **Telecom** records the single highest absolute chargeback volume. Within Telecom, **13.26% of transactions resulted in customer disputes**, marking it as a priority audit sector.

---

### Figure 10: Chargeback Severity Distribution
![Dispute Severity](reports/figures/m4/10_cb_severity.png)
- **Path**: `reports/figures/m4/10_cb_severity.png`
- **Insight**: Classifies disputes into Critical, High, Medium, and Low severity tiers, enabling triage protocols for operations and compliance teams.

---

### Figure 11: Transaction Amount Distribution & Outliers
![Amount Distribution](reports/figures/m4/11_amount_distribution.png)
- **Path**: `reports/figures/m4/11_amount_distribution.png`
- **Insight**: Highlights long-tailed transaction distributions with extreme positive outliers and 420 negative amounts (accounting for ₹-5.27M net negative adjustments).

---

### Figure 12: Customer KYC Status Breakdown
![KYC Status](reports/figures/m4/12_kyc_status.png)
- **Path**: `reports/figures/m4/12_kyc_status.png`
- **Insight**: Shows the split between VERIFIED, PENDING, REJECTED, and UNVERIFIED customers. Highlighting that unverified customer transactions exhibit elevated dispute probabilities.

---

### Figure 13: Merchant Chargeback Rate vs Volume Scatter
![Merchant CB Rate vs Volume](reports/figures/m4/13_merchant_cb_rate_vs_volume.png)
- **Path**: `reports/figures/m4/13_merchant_cb_rate_vs_volume.png`
- **Insight**: Crucial risk plot: isolates low-volume high-risk anomaly merchants in the top-left quadrant from high-volume stable merchants in the bottom-right quadrant.

---

### Figure 14: Day of Week Transaction Volume
![Day of Week Volume](reports/figures/m4/14_day_of_week_volume.png)
- **Path**: `reports/figures/m4/14_day_of_week_volume.png`
- **Insight**: **Tuesday** represents the highest processing volume of the week, with steady activity across weekdays and reduced volume on weekends.

---

### Figure 15: Data Quality Summary Dashboard
![Data Quality Summary](reports/figures/m4/15_data_quality_summary.png)
- **Path**: `reports/figures/m4/15_data_quality_summary.png`
- **Insight**: High-level visual scorecard summarizing the proportion of missing UTRs (5.0%), negative amounts (2.1%), unlinked KYC (67.6%), and unlinked merchants (51.8%).

---

## 6. Core Business Insights & Financial Metrics

Derived deterministically from the unified model (`finguard_transactions.csv`) and validated in [`reports/m4_insights.md`](reports/m4_insights.md):

| # | Metric / Insight | Exact Value | Operational Significance |
|---|---|---|---|
| **1** | **Total Processed Volume** | **20,000 transactions** | 100% data conservation achieved; zero rows dropped. |
| **2** | **Total Transaction Value** | **₹239,232,643.30** | Gross value excluding negative anomalies is ₹244,502,576.06. |
| **3** | **Transaction Success Rate** | **85.26% (17,053 txns)** | Core baseline network throughput. |
| **4** | **Transaction Failure Rate** | **9.78% (1,955 txns)** | Benchmark failure baseline across banking gateways. |
| **5** | **Overall Chargeback Rate** | **12.255% (2,451 txns)** | Disputed transaction frequency across portfolio. |
| **6** | **Total Disputed Value** | **₹6,342,602.86** | Accounts for **2.651% of total transaction value**. |
| **7** | **Dispute Reporting Delay** | **44.96% > 7 days (1,102 disputes)** | Median delay is **846.16 hours (~35.2 days)**, indicating delayed fraud discovery. |
| **8** | **Negative Value Anomalies** | **420 transactions (2.1%)** | Total net negative value ₹-5,269,932.76 flagged as accounting/reversal anomalies. |
| **9** | **Missing UTR Traceability** | **1,000 transactions (5.0%)** | Reconciliation gaps flagged with `missing_utr = True`. |
| **10** | **KYC Coverage Gap** | **67.61% unlinked (13,522 txns)** | Only 32.39% of transacting users match the KYC master table. |
| **11** | **Merchant Master Gap** | **51.84% unlinked (10,369 txns)** | Transacting merchants absent from merchant master registry. |
| **12** | **Top Dispute Category** | **TELECOM (13.26% CB rate)** | Highest absolute chargeback count across 44 categories. |
| **13** | **Peak Activity Hours** | **Peak: 00:00–01:00 \| Failures: 11:00** | Night-time batch velocity vs mid-day gateway throttling. |
| **14** | **Top Disputing User** | **USR58627 (4 disputes, ₹34,493.48)** | Identified as primary repeated-dispute investigation candidate. |
| **15** | **Merchant Concentration** | **Top 5 = 0.23% volume** | Highly fragmented long-tail merchant network. |

---

## 7. Explainable Risk Scoring Methodology

FinGuard enforces a deterministic point allocation system detailed in [`reports/m6_risk_methodology.md`](reports/m6_risk_methodology.md):

### Mode A: Real-Time Transaction Scoring (Max 100 Points)
*Strictly zero lookahead bias; evaluates only signals observable at transaction moment.*
- **`kyc_rejected_unverified` (25 pts)**: User KYC failed, rejected, or missing.
- **`historical_user_failure_rate` (25 pts)**: Expanding user failure rate shifted by 1.
- **`amount_anomaly_user_relative` (25 pts)**: Amount deviation exceeding 3 standard deviations from user history.
- **`missing_utr` (15 pts)**: Missing UTR creates reconciliation untraceability.
- **`invalid_timestamp` (10 pts)**: Epoch or unparseable timestamp anomaly.

### Mode B: Retrospective Post-Dispute Scoring (Max 100 Points)
*Used for triage, merchant audits, and ring investigations.*
- **`merchant_chargeback_rate` (35 pts)**: Historical dispute ratio of merchant.
- **`user_chargeback_rate` (35 pts)**: Historical dispute frequency of customer.
- **`merchant_disputed_amount_ratio` (25 pts)**: Disputed INR relative to gross turnover.
- **`delayed_dispute_rate` (15 pts)**: Disputes filed > 7 days post transaction.
- **`kyc_duplicate_entity_flag` (10 pts)**: Shared PAN/Aadhaar entities across multiple IDs.

---

## 8. Graph Intelligence & Fraud Ring Detection

FinGuard's graph engine (`src/risk/graph_engine.py`) builds a bipartite graph representation stored in `data/processed/graph/`:

```
   (USER A) ─────────── [TXN 101] ───────────> (MERCHANT X)
        │                                           ▲
        │                                           │
   [TXN 102]                                   [TXN 103]
        │                                           │
        ▼                                           │
   (MERCHANT Y) <────── [TXN 104] ─────────── (USER B)
```

- **Graph Scale**:
  - Total Nodes: **25,929** (17,878 Users, 8,051 Merchants)
  - Total Transaction Edges: **20,000**
  - Chargeback Edges: **2,800**
- **Ring Identification (`suspicious_clusters.csv`)**:
  - Connected component extraction identifies isolated subgraphs.
  - Computes internal cluster dispute density, velocity spikes, and shared entity linkage.
  - Allows compliance officers to isolate organized merchant-user collusion rings without manual spreadsheet queries.

---

## 9. Executive Investigation Dashboard

Built with React 18, TypeScript, Tailwind CSS, and Lucide icons in [`dashboard/`](dashboard/).

### Dashboard Capabilities:
1. **Executive Overview**: High-level KPI cards (Total Volume, INR Value, Failure Rate, Chargeback Rate, Active Rings), volume trends, and category distribution.
2. **Merchant Intelligence**: Searchable and sortable registry of 8,051 merchants with risk tier tags, dispute ratios, transaction velocity, and ticket sizes.
3. **Risk Intelligence**: Dual-mode transaction scoring viewer with live explainability breakdowns and signal attribution.
4. **Graph Investigation Explorer**: Visual network explorer rendering bipartite user-merchant connections, cluster memberships, and high-risk subgraphs.

To launch locally:
```bash
cd dashboard
npm install
npm run dev
```

---

## 10. Autonomous AI Copilot & Safety Guardrails

Located in [`src/m9_agent/`](src/m9_agent/), FinGuard features an AI Investigation Copilot with deterministic function calling:

### Tool Registry:
- `get_user_profile(user_id)`: Fetches KYC status, transaction count, risk tier, and dispute history.
- `get_merchant_profile(merchant_id)`: Retrieves category, onboarding date, dispute ratio, and volume.
- `get_transaction_details(txn_id)`: Returns point-in-time features, amount, UTR, and risk score.
- `explain_cluster(cluster_id)`: Explains graph cluster topology, member count, and ring signals.
- `search_high_risk_entities(entity_type, limit)`: Surfaces top investigation candidates.

### M10 Enterprise Safety Guardrails (`safety_guard.py`):
- **Defamation & Unsubstantiated Claim Filter**: Blocks terms like "confirmed fraud", "guilty syndicate", or "proven criminal" since ground-truth labels do not exist.
- **Sanitized Investigation Vocabulary**: Translates findings into safe, auditable language ("elevated-risk investigation candidate", "anomalous behavioral pattern").
- **Audit Logging**: Every query, tool execution, and response is logged with timestamps in [`reports/m8_gemini_audit.md`](reports/m8_gemini_audit.md).

---

## 11. How to Run & Reproduce (Quickstart)

Run the full end-to-end FinGuard pipeline with these standard commands:

```bash
# 1. Clone repository & install dependencies
git clone https://github.com/aditya242007/FinGuard.git
cd FinGuard
pip install -r requirements.txt

# 2. Run Data Quality Audit (M1)
python -m src.quality.audit

# 3. Run Cleaning & Normalization Pipeline (M2)
python -m src.cleaning.pipeline
python -m src.cleaning.diagnostics

# 4. Build Unified Data Model & Star Schema (M3)
python -m src.integration.build_model

# 5. Generate All 15 Figures & KPI Reports (M4)
python -m src.eda.generate_figures
python -m src.eda.generate_kpis

# 6. Build Feature Store (M5)
python -m src.features.build_features

# 7. Run Explainable Risk Scoring Engine (M6)
python -m src.risk.engine

# 8. Run Graph Analytics & Fraud Ring Detection (M7)
python -m src.risk.graph_engine

# 9. Run the Full Automated Test Suite (241 tests)
pytest tests/ -v

# 10. Start the Executive Dashboard (M8)
cd dashboard
npm install
npm run dev
```

---

## 12. Verification & Test Results Summary

FinGuard's codebase is validated by a 241-test automated suite ensuring total mathematical correctness and data integrity:

```
============================= 241 passed, 10 skipped in 172.98s =============================
```

- **M1 Audit Engine**: 15 tests verifying schema profiling, null counts, and format diagnostics.
- **M2 Cleaning & Normalization**: 42 tests verifying regex normalization, epoch timestamp conversion, currency stripping, and status mapping.
- **M3 Integration & Reconciliation**: 28 tests proving exact 20,000/20,000 transaction row conservation and foreign key join integrity.
- **M5 Feature Engineering**: 32 tests asserting zero lookahead bias and correct expanding window math.
- **M6 Risk Scoring Engine**: 35 tests verifying 0–100 score bounds, monotonic weight additions, and explanation generation.
- **M7 Graph Engine**: 44 tests asserting node uniqueness, edge validity, and cluster detection.
- **M8 Dashboard Data Contract**: 18 tests asserting JSON API schemas and TypeScript interface alignment.
- **M9 & M10 Agent & Safety**: 27 tests verifying tool function calling schemas, regex safety interceptors, and red-team evasion protection.

---
*Created for the TransOrg AgentIQ Datathon — Track 1: FinTech & BFSI.*
