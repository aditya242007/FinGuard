# M8 Dashboard Audit Report

**Executive Verdict:**
M8 AUDIT: FAIL

## Executive Summary
While the M8 dashboard successfully preserves M0-M7 output integrity and correctly implements M7 cluster chargeback logic without modifying underlying data, the frontend implementation is deeply flawed. The dashboard fails to load the correct Total Transaction Value due to a mapping error, implements only half of the requested global filters, lacks true graph drill-down capabilities, and relies on an unscalable client-side CSV parsing architecture. The dashboard acts more like a static mock-up than an interactive FinTech intelligence product.

---

## 1. DATA CORRECTNESS
**Status: FAIL**
- **Evidence (Total Value KPI):** The `Overview.tsx` calculates Total Value using `t.amount_abs` (`filteredData.reduce((sum, t) => sum + (t.amount_abs || 0), 0)`). However, `amount_abs` does not exist in the `finguard_transactions.csv` file (only `amount_numeric` is present). This results in a Total Value of ₹0 instead of the authoritative ₹239,232,643.30. (Severity: **CRITICAL**)
- **Evidence (KPI Filtering):** The "Suspicious Clusters" and "High/Critical Entities" KPI cards in `Overview.tsx` use the raw data arrays (`data.clusters.length`) instead of dynamically recalculating based on the active global filters. (Severity: **HIGH**)

## 2. M6 INTEGRATION
**Status: FAIL**
- **Evidence (Transaction Risk Visibility):** The UI fails to distinguish between transaction-time risk and retrospective risk for individual transactions. In `InvestigationExplorer.tsx`, when searching for a transaction, no risk scores or explanations are displayed at all. (Severity: **HIGH**)
- **Evidence (Merchant Risk Visibility):** While `RiskIntelligence.tsx` correctly displays the retrospective score for merchants, it fails to display specific risk explanations for them. (Severity: **MEDIUM**)

## 3. M7 INTEGRATION
**Status: PASS**
- **Evidence (CLU00604 Correctness):** M7 data was preserved. `data/processed/graph/suspicious_clusters.csv` has `cluster_chargeback_rate` = 1.0 (100%), and `chargeback_count` = 2. The `formatPercent` utility in `format.ts` successfully renders this as 100% without exceeding 1. No fraud-probability claims were found.

## 4. GLOBAL FILTERS
**Status: FAIL**
- **Evidence (Missing Filters):** `FilterBar.tsx` only implements filters for Status, Merchant Category, Risk Level, and Chargeback presence. Date, Merchant, User, and KYC Status filters are entirely missing. (Severity: **HIGH**)
- **Evidence (Filter Application):** As noted above, the implemented filters only modify the `filteredData` transaction array, leaving Cluster and Merchant aggregations unaffected. (Severity: **HIGH**)

## 5. DRILL-DOWNS
**Status: FAIL**
- **Evidence (Fake Drill-downs):** True graph traversal (transaction → user → merchant → chargeback) does not exist. `InvestigationExplorer.tsx` relies on a naive `.find()` text search (`c.cluster_id.includes(searchTerm)`) and only returns hardcoded top-level cluster or transaction details. (Severity: **CRITICAL**)

## 6. RISK EXPLAINABILITY
**Status: INVESTIGATE**
- **Evidence (Incomplete Explainability):** `InvestigationExplorer.tsx` correctly renders the `explanation` and `top_signals` fields for clusters, but individual transactions and merchants do not display any risk explanations or behavioral signals. (Severity: **HIGH**)

## 7. DATA QUALITY
**Status: FAIL**
- **Evidence (Missing Data Quality Metrics):** The Data Quality Snapshot panel in `Overview.tsx` correctly surfaces Missing KYC, Missing UTR, and Negative Amounts. However, it completely fails to show the crucial Unmatched Merchant KPI (10,369 transactions, 51.84%). (Severity: **HIGH**)

## 8. CHARTS
**Status: INVESTIGATE**
- **Evidence (Chart Limitations):** `MerchantIntelligence.tsx` contains a static Recharts bar chart restricted to the top 15 categories by value. It lacks tooltips for underlying behavioral signals and drill-down functionality. (Severity: **MEDIUM**)

## 9. UX
**Status: FAIL**
- **Evidence (Truncation vs Pagination):** Tables in `RiskIntelligence.tsx` are hardcoded to show only 10 rows using `.slice(0, 10)`, acting as a static preview rather than an interactive explorer. (Severity: **HIGH**)

## 10. PERFORMANCE
**Status: FAIL**
- **Evidence (Browser Memory Bloat):** `utils/dataLoader.ts` fetches and parses all full-size CSV files directly into the browser's memory using `PapaParse` on initial load. This approach will freeze the browser as dataset size grows. (Severity: **CRITICAL**)
- **Evidence (Main-Thread Filtering):** `InvestigationExplorer.tsx` executes `.find()` loops over 20,000+ unindexed rows on every keystroke in the main thread without debouncing. (Severity: **HIGH**)

## 11. REPRODUCIBILITY
**Status: PASS WITH MINOR FIXES**
- **Evidence:** `prepare_dashboard_data.py` accurately copies data files from `data/processed` without modifying M3-M7 logic. 

## 12. REGRESSION
**Status: PASS**
- **Evidence:** `pytest` executed successfully (143 passed, 2 warnings) in the background task. M8 has not broken previous milestones.

---

### Recommended Fixes (To be implemented later):
1. **Data Model:** Update `dataLoader.ts` and `Overview.tsx` to map `amount_numeric` instead of `amount_abs`.
2. **Global Filters:** Add the missing filters (Date, User, Merchant, KYC) to `useFilterStore.ts` and `FilterBar.tsx`. Ensure they apply to *all* dashboard components, including KPI cards.
3. **Drill-downs:** Rebuild `InvestigationExplorer.tsx` to display relationships visually or through interactive nested tables.
4. **Data Quality:** Add "Unmatched Merchants" to the Data Quality panel in `Overview.tsx`.
5. **Architecture:** Migrate from client-side `PapaParse` to a backend API or pre-computed JSON indices to resolve memory and performance issues.
