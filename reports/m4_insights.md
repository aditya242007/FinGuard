# FinGuard M4.1 — Business Insights

> **Note:** This analysis identifies behavioral patterns and risk signals. It does not establish confirmed fraud without ground-truth fraud labels.

- 1. Transaction success rate is 85.26% (17,053 of 20,000 transactions). Failure rate is 9.78% (1,955 transactions).

- 2. Peak transaction hour is 0:00–1:00. Highest failure rate occurs at hour 11:00.

- 3. Tuesday has the highest transaction volume among all days of the week.

- 4. Merchant category 'TELECOM' accounts for 2.2% of all transactions. Transactions are spread across 44 distinct categories.

- 5. The top 5 merchants by transaction count account for 45 of 20,000 transactions (0.23%).

- 6. Chargeback rate is 12.255% (2,451 transactions). Total disputed amount is ₹6,342,602.86, representing 2.6512% of total transaction value.

- 7. 1102 disputes (44.96%) were reported more than 7 days after the transaction. Median reporting delay is 846.16 hours.

- 8. 67.61% of transactions (13,522) lack KYC enrichment. User-level KYC segmentation covers only 32.39% of transaction volume.

- 9. 51.84% of transactions (10,369) have no matching merchant master record, limiting merchant-level enrichment for that proportion.

- 10. 420 transactions (2.1%) have negative amounts. Total transaction value including negatives is ₹239,232,643.30; excluding negatives is ₹244,502,576.06; the net negative contribution is ₹-5,269,932.76. Negative‑value records are retained as data‑quality or behavioral anomalies.

- 11. 5.0% of transactions (1,000) are missing a UTR reference. UTR is required for reconciliation; missing UTR reduces traceability for those transactions.

- 12. 0 invalid timestamps means timestamps are suitable for the current time-series analysis.

- 13. Merchant category 'TELECOM' has the highest absolute chargeback count. Within that category, 13.26% of its transactions resulted in a chargeback. This is a potential risk signal, not confirmed fraud.

- 14. User 'USR58627' has the highest chargeback count (4 chargebacks, ₹34,493.48 disputed). Top-5 repeated-dispute users warrant further investigation.

- 15. 0 transactions (0.0%) share a normalized transaction ID with at least one other record. Entity resolution has not yet been applied to transaction IDs — this affects deduplication confidence.

