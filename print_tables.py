import pandas as pd
from src.eda.m4_eda_fixes import load_data, telecom_summary, top_user_summary, compute_delay_stats, anomaly_summary
txn, usr, mrc, cb = load_data()
cat, telecom_row = telecom_summary(txn, cb)
print("=== TELECOM SUMMARY ===")
print(telecom_row)
print("\n=== TOP USERS ===")
print(top_user_summary(usr, txn))
print("\n=== DELAY STATS ===")
print(compute_delay_stats(txn))
print("\n=== ANOMALY SUMMARY ===")
print(anomaly_summary(txn))
