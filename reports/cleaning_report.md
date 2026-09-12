# FinGuard Data Cleaning & Normalization Report

## Overview
This report summarizes the cleaning and normalization applied to the raw datasets.

## Dataset Statistics
| Dataset | Raw Rows | Processed Rows | Exact Duplicates Removed |
| --- | --- | --- | --- |
| transactions | 20400 | 20000 | 400 |
| kyc | 36400 | 36122 | 278 |
| merchants | 6210 | 6198 | 12 |
| chargebacks | 2884 | 2800 | 84 |

## Referential Integrity (After Normalization)
| Missing FK | Count |
| --- | --- |
| txn_user_fk_missing | 13522 |
| txn_merchant_fk_missing | 10369 |
| cb_txn_fk_missing | 116 |
| cb_user_fk_missing | 1915 |
| cb_merchant_fk_missing | 1501 |