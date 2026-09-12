# FinGuard Post-Cleaning Validation & Join Diagnostics

## 1. ID Normalization Validation

### KYC user_id
- Raw unique: 32165
- Normalized unique: 28920
- Collision groups (>1 raw per norm): 3089
- Examples:
  - USR10049 <- USR10049, usr10049
  - USR10233 <- USR10233, USR 10233
  - USR10239 <- 10239, USR10239
  - USR10288 <- USR10288, usr10288
  - USR10310 <- USR-10310, USR 10310

### Merchant merchant_id
- Raw unique: 5083
- Normalized unique: 4343
- Collision groups (>1 raw per norm): 690
- Examples:
  - MCH1014 <- MCH1014, MCH 1014
  - MCH1016 <- MCH1016, MCH 1016
  - MCH1032 <- MCH 1032, mch1032
  - MCH1033 <- MCH-1033, MCH1033
  - MCH1039 <- 1039, mch1039

### Transaction txn_id
- Raw unique: 20000
- Normalized unique: 20000
- Collision groups (>1 raw per norm): 0

### Chargeback complaint_id
- Raw unique: 2800
- Normalized unique: 2800
- Collision groups (>1 raw per norm): 0

## 2. Transaction -> KYC Matching

- Matched IDs: 5799
- Unmatched IDs: 12079
- Match %: 32.44%
- Example unmatched normalized IDs:
  USR35532, USR27682, USR75989, USR70727, USR84401, USR58062, USR77508, USR31183, USR27758, USR36703, USR99157, USR75482, USR87291, USR88669, USR30674, USR42003, USR87362, USR89922, USR43044, USR70415

## 3. Transaction -> Merchant Matching

- Matched IDs: 3893
- Unmatched IDs: 4158
- Match %: 48.35%
- Example unmatched normalized IDs:
  MCH8463, MCH6132, MCH8009, MCH1648, MCH6901, MCH9746, MCH6089, MCH4607, MCH6910, MCH8961, MCH8812, MCH2333, MCH1693, MCH6658, MCH8190, MCH9372, MCH2866, MCH8347, MCH3320, MCH1282

## 4. Chargeback Joins

### Chargeback -> Transaction
- Match %: 95.48% (2451 matched, 116 unmatched)
### Chargeback -> KYC
- Match %: 31.78% (729 matched, 1565 unmatched)
### Chargeback -> Merchant
- Match %: 46.68% (866 matched, 989 unmatched)

## 5. Symmetry Check

- User ID symmetry pass: True
- Merchant ID symmetry pass: True

## 6. Column Survival

- transactions: PASS
- kyc: PASS
- merchants: PASS
- chargebacks: PASS

## 7. Data Loss Check

- transactions: PASS (20400 -> 20000, diff=400)
- kyc: PASS (36400 -> 36122, diff=278)
- merchants: PASS (6210 -> 6198, diff=12)
- chargebacks: PASS (2884 -> 2800, diff=84)

## 8. Negative Values Check

- Transactions with negative amount flag: 420
- Chargebacks with negative amount flag: 220

## 9. Lineage Check

- transactions: PASS
- kyc: PASS
- merchants: PASS
- chargebacks: PASS

## Conclusion
**OVERALL: PASS**