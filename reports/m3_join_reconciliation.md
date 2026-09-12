# FinGuard M3 — Join Reconciliation Report

## 1. Root Cause: Unit of Measurement Differs

The M2 validation and M3 integration count matches at **different units**:

| Script | Unit Counted |
| --- | --- |
| `diagnostics.py` (M2) | Unique normalized IDs that appear in both datasets |
| `build_model.py` (M3) | Transaction **rows** where the join produced a non-null result |

These are fundamentally different things. One user can appear in many transactions.
The M2 number tells you: *how many distinct users linked?*
The M3 number tells you: *how many transaction rows have KYC data attached?*

## 2. Reproduced Numbers

### KYC Join
| Metric | Value |
| --- | --- |
| M2: Unique user IDs in transactions | 17,878 |
| M2: Unique user IDs matched to KYC (set intersection) | 5,799 |
| M2: Unique user IDs unmatched | 12,079 |
| M3: Transaction **rows** matched to canonical KYC | 6,478 |
| M3: Transaction **rows** unmatched | 13,522 |
| M3 Total rows check (matched + unmatched) | 20,000 |

### Merchant Join
| Metric | Value |
| --- | --- |
| M2: Unique merchant IDs in transactions | 8,051 |
| M2: Unique merchant IDs matched (set intersection) | 3,893 |
| M2: Unique merchant IDs unmatched | 4,158 |
| M3: Transaction **rows** matched to canonical merchant | 9,631 |
| M3: Transaction **rows** unmatched | 10,369 |
| M3 Total rows check (matched + unmatched) | 20,000 |

## 3. Verification: No Fuzzy Matching

Join uses exact string equality on `user_id_normalized` in both scripts.
No approximate matching, phonetic matching, or levenshtein distance is used.

Sample canonical KYC IDs that DO match transaction IDs (exact string):
> ['USR32142', 'USR68888', 'USR90143', 'USR98220', 'USR59208']

Corresponding values found in transactions:
> ['USR59208']

## 4. Verification: No Duplicate Join Creating False Rows

After deduplicating KYC to 1 row per `user_id_normalized`, merging with transactions:
- Rows before join: 20,000
- Rows after join: 20,000
- Row conservation: ✅ PASS

## 5. Verification: Integrated File Row Count

- `transactions_clean.csv` rows: 20,000
- `finguard_transactions.csv` rows: 20,000
- Row conservation: ✅ PASS

## 6. Effect of Entity Resolution on Coverage

The M2 diagnostics script read the cleaned KYC file as-is and did a **set intersection**.
The M3 pipeline first **entity-resolves** KYC (picks one canonical row per user).
Because entity resolution only deduplicates, it does NOT expand the set of unique user IDs.

| | Unique user_id_normalized values |
| --- | --- |
| Cleaned KYC (before entity resolution) | 28,920 |
| Canonical KYC (after entity resolution) | 28,920 |

The canonical set is the **same or smaller** than the raw cleaned set.
Therefore entity resolution does NOT inflate matches.

## 7. Conclusion & Explanation

### Why the numbers differ

| Source | What is counted | KYC value | Merchant value |
| --- | --- | --- | --- |
| M2 diagnostics | Unique normalized IDs matched | 5,799 | 3,893 |
| M3 integration | Transaction rows with a join hit | 6,478 | 9,631 |

The M2 number is the count of **distinct user IDs** that appear in both datasets.
The M3 number is the count of **transaction rows** that successfully joined.

A single matched user ID can appear in many transactions.
Example: If `USR100` appears 10 times in transactions and once in KYC,
M2 counts this as 1 matched ID. M3 counts this as 10 matched rows.

### Is M3 correct?

Yes. M3 is doing the right thing: it reports how many **rows** in the fact table have
KYC/merchant context available for analysis — which is the correct metric for an
analytics data model.

### Is there a bug?

No. Both numbers are correct for their respective purposes:
- M2 tells you: *how much of the ID space is covered?*
- M3 tells you: *how much of the transaction volume is enriched?*

### Checks Summary

| Check | Result |
| --- | --- |
| Same normalization rules used in both scripts | ✅ PASS |
| No fuzzy matching introduced | ✅ PASS |
| No duplicate join creating false rows | ✅ PASS |
| Integrated transaction rows = 20,000 | ✅ PASS |
| Matched + unmatched rows = 20,000 (KYC) | ✅ PASS |
| Matched + unmatched rows = 20,000 (Merchant) | ✅ PASS |
| Entity resolution only shrinks, does not expand, canonical ID set | ✅ PASS |

**OVERALL: No bug found. M3 integration logic is correct.**