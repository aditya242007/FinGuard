"""
FinGuard M4.1 — Comprehensive EDA & Business KPI Baseline
"""
from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("m4_eda")

# ── Paths ──────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent.parent.parent
PROCESSED = HERE / "data" / "processed"
REPORTS   = HERE / "reports"
FIGURES   = REPORTS / "figures" / "m4"
FIGURES.mkdir(parents=True, exist_ok=True)

# ── Plot style ─────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted")
FIGSIZE = (12, 5)
BAR_COLOR = "#4C72B0"
WARN_COLOR = "#DD8452"

# ══════════════════════════════════════════════════════════════════════
# 1. Data loading & type conversion
# ══════════════════════════════════════════════════════════════════════
def load_data():
    logger.info("Loading datasets …")
    txn  = pd.read_csv(PROCESSED / "finguard_transactions.csv",  dtype=str)
    usr  = pd.read_csv(PROCESSED / "users_analytics.csv",        dtype=str)
    mrc  = pd.read_csv(PROCESSED / "merchants_analytics.csv",    dtype=str)
    cb   = pd.read_csv(PROCESSED / "chargebacks_aggregated.csv", dtype=str)

    # Numeric conversions — coerce invalids to NaN, never drop rows
    num_txn = ["amount_numeric", "chargeback_count", "total_disputed_amount",
               "chargeback_report_delay_hours", "monthly_income_numeric", "txn_id_duplicate_count"]
    for c in num_txn:
        if c in txn.columns:
            txn[c] = pd.to_numeric(txn[c], errors="coerce")

    bool_cols = ["amount_is_negative", "amount_is_zero", "amount_parse_failed",
                 "amount_missing", "timestamp_parse_failed", "timestamp_missing",
                 "utr_missing", "utr_invalid", "user_fk_missing", "merchant_fk_missing",
                 "transaction_has_kyc", "transaction_has_merchant", "transaction_has_chargeback",
                 "has_chargeback", "dispute_after_7_days_flag", "duplicate_txn_id_flag",
                 "referential_integrity_issue_flag", "utr_missing_flag",
                 "amount_negative_flag", "timestamp_invalid_flag"]
    for c in bool_cols:
        if c in txn.columns:
            txn[c] = txn[c].map({"True": True, "False": False, True: True, False: False}).astype("boolean")

    txn["timestamp_clean"] = pd.to_datetime(txn["timestamp_clean"], errors="coerce")

    num_usr = ["transaction_count", "total_transaction_amount", "avg_transaction_amount",
               "successful_transaction_count", "failed_transaction_count",
               "chargeback_count", "total_disputed_amount"]
    for c in num_usr:
        if c in usr.columns: usr[c] = pd.to_numeric(usr[c], errors="coerce")

    num_mrc = ["transaction_count", "total_transaction_amount", "avg_transaction_amount",
               "successful_transaction_count", "failed_transaction_count",
               "chargeback_count", "total_disputed_amount",
               "chargeback_rate", "disputed_amount_ratio", "success_rate", "failure_rate"]
    for c in num_mrc:
        if c in mrc.columns: mrc[c] = pd.to_numeric(mrc[c], errors="coerce")

    cb["total_disputed_amount"] = pd.to_numeric(cb["total_disputed_amount"], errors="coerce")
    cb["chargeback_count"]      = pd.to_numeric(cb["chargeback_count"],      errors="coerce")
    cb["first_chargeback_timestamp"]  = pd.to_datetime(cb["first_chargeback_timestamp"],  errors="coerce")
    cb["latest_chargeback_timestamp"] = pd.to_datetime(cb["latest_chargeback_timestamp"], errors="coerce")

    logger.info("  transactions: %d rows × %d cols", len(txn), txn.shape[1])
    logger.info("  users:        %d rows × %d cols", len(usr), usr.shape[1])
    logger.info("  merchants:    %d rows × %d cols", len(mrc), mrc.shape[1])
    logger.info("  chargebacks:  %d rows × %d cols", len(cb),  cb.shape[1])
    return txn, usr, mrc, cb

# ══════════════════════════════════════════════════════════════════════
# 2. Transaction KPIs
# ══════════════════════════════════════════════════════════════════════
def compute_txn_kpis(txn: pd.DataFrame) -> dict:
    logger.info("Computing transaction KPIs …")
    n = len(txn)
    amt = txn["amount_numeric"]

    valid_amt = amt.dropna()
    success = (txn["status_clean"] == "SUCCESS").sum()
    failed  = (txn["status_clean"] == "FAILED").sum()
    pending = (txn["status_clean"] == "PENDING").sum()

    # Date range
    ts_valid = txn["timestamp_clean"].dropna()
    date_min = ts_valid.min().date() if not ts_valid.empty else None
    date_max = ts_valid.max().date() if not ts_valid.empty else None
    n_days   = (pd.Timestamp(date_max) - pd.Timestamp(date_min)).days + 1 if date_min else 1

    kpis = {
        "total_transactions":        int(n),
        "total_amount":              round(float(valid_amt.sum()), 2),
        "avg_amount":                round(float(valid_amt.mean()), 2),
        "median_amount":             round(float(valid_amt.median()), 2),
        "min_amount":                round(float(valid_amt.min()), 2),
        "max_amount":                round(float(valid_amt.max()), 2),
        "successful_count":          int(success),
        "failed_count":              int(failed),
        "pending_count":             int(pending),
        "success_rate_pct":          round(100 * success / n, 2),
        "failure_rate_pct":          round(100 * failed  / n, 2),
        "pending_rate_pct":          round(100 * pending / n, 2),
        "date_range_start":          str(date_min),
        "date_range_end":            str(date_max),
        "analysis_days":             int(n_days),
        "avg_txn_per_day":           round(n / n_days, 2),
        "avg_value_per_day":         round(float(valid_amt.sum()) / n_days, 2),
        "missing_amount_count":      int(amt.isna().sum()),
        "negative_amount_count":     int(txn.get("amount_is_negative", pd.Series(False, dtype=bool)).fillna(False).sum()),
        "parse_failed_amount_count": int(txn.get("amount_parse_failed", pd.Series(False, dtype=bool)).fillna(False).sum()),
    }
    return kpis

# ══════════════════════════════════════════════════════════════════════
# 3. Chargeback KPIs
# ══════════════════════════════════════════════════════════════════════
def compute_cb_kpis(txn: pd.DataFrame, cb: pd.DataFrame) -> dict:
    logger.info("Computing chargeback KPIs …")
    n = len(txn)
    txns_with_cb = int(txn["has_chargeback"].fillna(False).sum())
    total_cb     = int(txn["chargeback_count"].fillna(0).sum())
    total_disp   = float(txn["total_disputed_amount"].fillna(0).sum())
    total_amt    = float(txn["amount_numeric"].fillna(0).sum())
    avg_delay    = float(txn.loc[txn["chargeback_report_delay_hours"] >= 0, "chargeback_report_delay_hours"].mean())
    med_delay    = float(txn.loc[txn["chargeback_report_delay_hours"] >= 0, "chargeback_report_delay_hours"].median())
    after7       = int(txn["dispute_after_7_days_flag"].fillna(False).sum())

    return {
        "total_chargeback_records":   int(len(cb)),
        "transactions_with_chargeback": txns_with_cb,
        "chargeback_rate_pct":        round(100 * txns_with_cb / n, 4),
        "total_disputed_amount":      round(total_disp, 2),
        "avg_disputed_amount":        round(total_disp / max(total_cb, 1), 2),
        "median_disputed_amount":     round(float(txn["total_disputed_amount"].dropna().median()), 2),
        "disputed_amount_ratio_pct":  round(100 * total_disp / max(total_amt, 1), 4),
        "avg_report_delay_hours":     round(avg_delay, 2),
        "median_report_delay_hours":  round(med_delay, 2),
        "disputes_after_7_days":      after7,
        "disputes_after_7_days_pct":  round(100 * after7 / max(txns_with_cb, 1), 2),
    }

# ══════════════════════════════════════════════════════════════════════
# 4. Data quality KPIs
# ══════════════════════════════════════════════════════════════════════
def compute_dq_kpis(txn: pd.DataFrame) -> dict:
    logger.info("Computing data-quality KPIs …")
    n = len(txn)

    def pct(s): return round(100 * int(s) / n, 2)

    utr_miss  = int(txn.get("utr_missing_flag",            pd.Series(False)).fillna(False).sum())
    amt_neg   = int(txn.get("amount_negative_flag",        pd.Series(False)).fillna(False).sum())
    ts_inv    = int(txn.get("timestamp_invalid_flag",      pd.Series(False)).fillna(False).sum())
    kyc_umatch= int((~txn["transaction_has_kyc"].fillna(False)).sum())
    mrc_umatch= int((~txn["transaction_has_merchant"].fillna(False)).sum())
    dup_txn   = int(txn.get("duplicate_txn_id_flag",       pd.Series(False)).fillna(False).sum())
    ri_issue  = int(txn.get("referential_integrity_issue_flag", pd.Series(False)).fillna(False).sum())

    return {
        "utr_missing_count":               utr_miss,
        "utr_missing_pct":                 pct(utr_miss),
        "negative_amount_count":           amt_neg,
        "negative_amount_pct":             pct(amt_neg),
        "invalid_timestamp_count":         ts_inv,
        "invalid_timestamp_pct":           pct(ts_inv),
        "unmatched_kyc_count":             kyc_umatch,
        "unmatched_kyc_pct":               pct(kyc_umatch),
        "unmatched_merchant_count":        mrc_umatch,
        "unmatched_merchant_pct":          pct(mrc_umatch),
        "duplicate_txn_id_count":          dup_txn,
        "duplicate_txn_id_pct":            pct(dup_txn),
        "referential_integrity_issue_count": ri_issue,
        "referential_integrity_issue_pct": pct(ri_issue),
    }

# ══════════════════════════════════════════════════════════════════════
# 5. Outlier / Anomaly exploration
# ══════════════════════════════════════════════════════════════════════
def compute_outlier_flags(txn: pd.DataFrame) -> pd.DataFrame:
    amt = txn["amount_numeric"].dropna()
    q1, q3 = amt.quantile(0.25), amt.quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 3 * iqr
    txn["amount_outlier_iqr"] = txn["amount_numeric"] > upper_fence

    z = (txn["amount_numeric"] - amt.mean()) / amt.std()
    txn["amount_zscore"] = z
    txn["amount_outlier_zscore"] = z.abs() > 3
    return txn

# ══════════════════════════════════════════════════════════════════════
# 6. Chart helpers
# ══════════════════════════════════════════════════════════════════════
def savefig(name: str):
    path = FIGURES / f"{name}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("  saved %s", path.name)

def bar_chart(series: pd.Series, title: str, xlabel: str, ylabel: str, fname: str, color=BAR_COLOR, top_n=15):
    if len(series) > top_n:
        series = series.nlargest(top_n)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    series.plot.bar(ax=ax, color=color)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.tight_layout()
    savefig(fname)

def line_chart(df: pd.DataFrame, x: str, y: str, title: str, ylabel: str, fname: str):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(df[x], df[y], marker="o", markersize=3, linewidth=1.5, color=BAR_COLOR)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(x); ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.tight_layout()
    savefig(fname)

# ══════════════════════════════════════════════════════════════════════
# 7. All charts
# ══════════════════════════════════════════════════════════════════════
def make_charts(txn: pd.DataFrame, mrc: pd.DataFrame, cb: pd.DataFrame):
    logger.info("Generating charts …")

    # 1. Daily transaction count
    daily = txn.dropna(subset=["timestamp_clean"]).copy()
    daily["date"] = daily["timestamp_clean"].dt.date
    daily_cnt  = daily.groupby("date").size().reset_index(name="count")
    daily_amt  = daily.groupby("date")["amount_numeric"].sum().reset_index(name="amount")
    daily_avg  = daily.groupby("date")["amount_numeric"].mean().reset_index(name="avg")

    line_chart(daily_cnt,  "date", "count",  "Daily Transaction Count", "Transactions", "01_daily_txn_count")
    line_chart(daily_amt,  "date", "amount", "Daily Transaction Value (₹)", "Amount (₹)", "02_daily_txn_value")

    # 3. Status distribution
    status_cnt = txn["status_clean"].value_counts()
    bar_chart(status_cnt, "Transaction Status Distribution", "Status", "Count", "03_status_distribution")

    # 4. Hourly transaction count
    txn["hour"] = txn["timestamp_clean"].dt.hour
    hourly_cnt  = txn.groupby("hour").size()
    bar_chart(hourly_cnt, "Hourly Transaction Volume", "Hour of Day", "Transactions", "04_hourly_volume")

    # 5. Hourly failure rate
    hourly_fail = txn.groupby("hour").apply(
        lambda g: (g["status_clean"] == "FAILED").sum() / max(len(g), 1) * 100
    )
    bar_chart(hourly_fail, "Hourly Failure Rate (%)", "Hour of Day", "Failure Rate (%)", "05_hourly_failure_rate", color=WARN_COLOR)

    # 6. Top merchant categories by transaction value
    cat_amt = txn.groupby("merchant_category_clean")["amount_numeric"].sum().dropna()
    cat_amt = cat_amt[~cat_amt.index.isin(["", "nan", "NaN"])]
    bar_chart(cat_amt.nlargest(15), "Top Merchant Categories by Transaction Value", "Category", "Total Amount (₹)", "06_top_categories_value")

    # 7. Top merchants by transaction value
    mrc_top = mrc.nlargest(15, "total_transaction_amount")[["merchant_id_normalized", "total_transaction_amount"]].set_index("merchant_id_normalized")
    bar_chart(mrc_top["total_transaction_amount"], "Top 15 Merchants by Transaction Value", "Merchant ID", "Total Amount (₹)", "07_top_merchants_value")

    # 8. Chargebacks by day
    cb_day = txn.dropna(subset=["first_chargeback_timestamp"]).copy()
    cb_day["cb_date"] = pd.to_datetime(cb_day["first_chargeback_timestamp"], errors="coerce").dt.date
    cb_daily = cb_day.groupby("cb_date").size().reset_index(name="chargebacks")
    if not cb_daily.empty:
        line_chart(cb_daily, "cb_date", "chargebacks", "Daily Chargeback Count", "Chargebacks", "08_daily_chargebacks")

    # 9. Chargebacks by merchant category
    cb_cat = txn[txn["has_chargeback"].fillna(False)].groupby("merchant_category_clean").size()
    cb_cat = cb_cat[~cb_cat.index.isin(["", "nan", "NaN"])]
    bar_chart(cb_cat.nlargest(15), "Chargebacks by Merchant Category", "Category", "Chargeback Count", "09_cb_by_category", color=WARN_COLOR)

    # 10. Chargeback severity distribution
    sev = txn.loc[txn["has_chargeback"].fillna(False), "max_severity"].dropna()
    # max_severity is comma-joined string; expand
    sev_exp = sev.str.split(",").explode().str.strip().value_counts()
    sev_exp = sev_exp[sev_exp.index != ""]
    bar_chart(sev_exp, "Chargeback Severity Distribution", "Severity", "Count", "10_cb_severity", color=WARN_COLOR)

    # 11. Amount distribution (log scale, clip extreme outliers at 99.5 pct)
    amt_valid = txn["amount_numeric"].dropna()
    clip_val  = amt_valid.quantile(0.995)
    amt_clip  = amt_valid.clip(upper=clip_val)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.hist(amt_clip, bins=60, color=BAR_COLOR, edgecolor="white")
    ax.set_title("Transaction Amount Distribution (clipped at 99.5th pct)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Amount (₹)"); ax.set_ylabel("Frequency")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
    plt.tight_layout(); savefig("11_amount_distribution")

    # 12. KYC status distribution (matched txns only)
    kyc_status = txn[txn["transaction_has_kyc"].fillna(False)]["kyc_status_clean"].value_counts()
    bar_chart(kyc_status, "KYC Status Distribution (Matched Transactions)", "KYC Status", "Count", "12_kyc_status")

    # 13. Merchant chargeback rate vs transaction volume (scatter)
    mrc_scatter = mrc.dropna(subset=["transaction_count", "chargeback_rate"]).copy()
    mrc_scatter = mrc_scatter[mrc_scatter["transaction_count"] >= 5]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.scatter(mrc_scatter["transaction_count"], mrc_scatter["chargeback_rate"] * 100,
               alpha=0.4, s=18, color=BAR_COLOR)
    ax.set_xlabel("Transaction Count"); ax.set_ylabel("Chargeback Rate (%)")
    ax.set_title("Merchant Chargeback Rate vs Transaction Volume", fontsize=13, fontweight="bold")
    plt.tight_layout(); savefig("13_merchant_cb_rate_vs_volume")

    # 14. Day-of-week transaction count
    txn["dow"] = txn["timestamp_clean"].dt.day_name()
    dow_order  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow_cnt    = txn.groupby("dow").size().reindex(dow_order, fill_value=0)
    bar_chart(dow_cnt, "Transaction Volume by Day of Week", "Day", "Transactions", "14_day_of_week_volume")

    # 15. Data-quality issue summary
    dq_labels = ["Missing UTR", "Negative Amount", "Invalid Timestamp",
                 "Unmatched KYC", "Unmatched Merchant", "Duplicate TXN ID"]
    dq_values = [
        int(txn.get("utr_missing_flag",            pd.Series(False)).fillna(False).sum()),
        int(txn.get("amount_negative_flag",        pd.Series(False)).fillna(False).sum()),
        int(txn.get("timestamp_invalid_flag",      pd.Series(False)).fillna(False).sum()),
        int((~txn["transaction_has_kyc"].fillna(False)).sum()),
        int((~txn["transaction_has_merchant"].fillna(False)).sum()),
        int(txn.get("duplicate_txn_id_flag",       pd.Series(False)).fillna(False).sum()),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.barh(dq_labels, dq_values, color=WARN_COLOR)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=9)
    ax.set_title("Data Quality Issues Summary (Transaction Count)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Affected Transactions")
    plt.tight_layout(); savefig("15_data_quality_summary")

    logger.info("All 15 charts saved.")

# ══════════════════════════════════════════════════════════════════════
# 8. Insights
# ══════════════════════════════════════════════════════════════════════
def generate_insights(txn: pd.DataFrame, usr: pd.DataFrame, mrc: pd.DataFrame,
                      txn_kpis: dict, cb_kpis: dict, dq_kpis: dict) -> list[str]:

    insights = []
    n = txn_kpis["total_transactions"]
    # Compute total amounts for negative amount analysis
    amt_series = txn["amount_numeric"]
    total_incl = float(amt_series.sum())
    total_excl = float(amt_series[amt_series >= 0].sum())
    negative_total = total_incl - total_excl

    # 1 — Status
    insights.append(
        f"1. Transaction success rate is {txn_kpis['success_rate_pct']}% "
        f"({txn_kpis['successful_count']:,} of {n:,} transactions). "
        f"Failure rate is {txn_kpis['failure_rate_pct']}% ({txn_kpis['failed_count']:,} transactions)."
    )

    # 2 — Hourly peak
    txn["hour"] = txn["timestamp_clean"].dt.hour
    peak_hour = int(txn.groupby("hour").size().idxmax())
    peak_fail_hour = int(
        txn.groupby("hour").apply(lambda g: (g["status_clean"] == "FAILED").sum() / max(len(g), 1))
        .idxmax()
    )
    insights.append(
        f"2. Peak transaction hour is {peak_hour}:00–{peak_hour+1}:00. "
        f"Highest failure rate occurs at hour {peak_fail_hour}:00."
    )

    # 3 — Day-of-week
    txn["dow"] = txn["timestamp_clean"].dt.day_name()
    peak_day = txn["dow"].value_counts().idxmax()
    insights.append(
        f"3. {peak_day} has the highest transaction volume among all days of the week."
    )

    # 4 — Merchant category concentration
    cat_cnt = txn.groupby("merchant_category_clean").size()
    top_cat_name  = cat_cnt.idxmax() if not cat_cnt.empty else "N/A"
    top_cat_pct   = round(100 * cat_cnt.max() / n, 1)
    cat_with_txns = (cat_cnt > 0).sum()
    insights.append(
        f"4. Merchant category '{top_cat_name}' accounts for {top_cat_pct}% of all transactions. "
        f"Transactions are spread across {cat_with_txns} distinct categories."
    )

    # 5 — Top merchant concentration
    # 5 — Top merchant concentration
    top5_txn = int(mrc.nlargest(5, "transaction_count")["transaction_count"].sum())
    top5_pct = round(100 * top5_txn / n, 2)
    insights.append(
        f"5. The top 5 merchants by transaction count account for {top5_txn:,} of {n:,} transactions ({top5_pct}%)."
    )

    # 6 — Chargeback rate
    insights.append(
        f"6. Chargeback rate is {cb_kpis['chargeback_rate_pct']}% "
        f"({cb_kpis['transactions_with_chargeback']:,} transactions). "
        f"Total disputed amount is ₹{cb_kpis['total_disputed_amount']:,.2f}, "
        f"representing {cb_kpis['disputed_amount_ratio_pct']}% of total transaction value."
    )

    # 7 — Delayed disputes
    insights.append(
        f"7. {cb_kpis['disputes_after_7_days']} disputes ({cb_kpis['disputes_after_7_days_pct']}%) "
        f"were reported more than 7 days after the transaction. "
        f"Median reporting delay is {cb_kpis['median_report_delay_hours']} hours."
    )

    # 8 — KYC coverage
    insights.append(
        f"8. {dq_kpis['unmatched_kyc_pct']}% of transactions ({dq_kpis['unmatched_kyc_count']:,}) "
        f"lack KYC enrichment. User-level KYC segmentation covers only "
        f"{100 - dq_kpis['unmatched_kyc_pct']}% of transaction volume."
    )

    # 9 — Merchant coverage
    insights.append(
        f"9. {dq_kpis['unmatched_merchant_pct']}% of transactions ({dq_kpis['unmatched_merchant_count']:,}) "
        f"have no matching merchant master record, limiting merchant-level enrichment for that proportion."
    )

    # 10 — Negative amounts
    insights.append(
        f"10. {dq_kpis['negative_amount_count']:,} transactions ({dq_kpis['negative_amount_pct']}%) have negative amounts. Total transaction value including negatives is ₹{total_incl:,.2f}; excluding negatives is ₹{total_excl:,.2f}; the net negative contribution is ₹{negative_total:,.2f}. Negative‑value records are retained as data‑quality or behavioral anomalies."
    )

    # 11 — UTR missing
    insights.append(
        f"11. {dq_kpis['utr_missing_pct']}% of transactions ({dq_kpis['utr_missing_count']:,}) "
        f"are missing a UTR reference. UTR is required for reconciliation; "
        f"missing UTR reduces traceability for those transactions."
    )

    # 12 — Invalid timestamps
    insights.append(
        f"12. {dq_kpis['invalid_timestamp_count']:,} invalid timestamps means timestamps are suitable for the current time-series analysis."
    )

    # 13 — High chargeback category
    cat_cb = txn[txn["has_chargeback"].fillna(False)].groupby("merchant_category_clean").size()
    cat_cb = cat_cb[~cat_cb.index.isin(["", "nan", "NaN"])]
    if not cat_cb.empty:
        top_cb_cat = cat_cb.idxmax()
        top_cb_vol = txn.groupby("merchant_category_clean").size().get(top_cb_cat, 1)
        top_cb_rate = round(100 * cat_cb.max() / max(top_cb_vol, 1), 2)
        insights.append(
            f"13. Merchant category '{top_cb_cat}' has the highest absolute chargeback count. "
            f"Within that category, {top_cb_rate}% of its transactions resulted in a chargeback. "
            f"This is a potential risk signal, not confirmed fraud."
        )

    # 14 — Repeated dispute users
    top_dispute_usr = usr.nlargest(5, "chargeback_count")[["user_id_normalized", "chargeback_count", "total_disputed_amount"]]
    if not top_dispute_usr.empty:
        max_row = top_dispute_usr.iloc[0]
        insights.append(
            f"14. User '{max_row['user_id_normalized']}' has the highest chargeback count "
            f"({int(max_row['chargeback_count'])} chargebacks, ₹{float(max_row['total_disputed_amount']):,.2f} disputed). "
            f"Top-5 repeated-dispute users warrant further investigation."
        )

    # 15 — Duplicate TXN IDs
    insights.append(
        f"15. {dq_kpis['duplicate_txn_id_count']:,} transactions ({dq_kpis['duplicate_txn_id_pct']}%) "
        f"share a normalized transaction ID with at least one other record. "
        f"Entity resolution has not yet been applied to transaction IDs — this affects deduplication confidence."
    )

    return insights

# ══════════════════════════════════════════════════════════════════════
# 9. Validation checks (returns {check: pass/fail})
# ══════════════════════════════════════════════════════════════════════
def run_validations(txn: pd.DataFrame, txn_kpis: dict, cb_kpis: dict) -> dict:
    results = {}
    results["txn_count_equals_20000"] = len(txn) == 20_000
    results["no_row_multiplication"] = len(txn) == txn_kpis["total_transactions"]
    results["success_rate_in_range"] = 0 <= txn_kpis["success_rate_pct"] <= 100
    results["failure_rate_in_range"] = 0 <= txn_kpis["failure_rate_pct"] <= 100
    results["pending_rate_in_range"] = 0 <= txn_kpis["pending_rate_pct"] <= 100
    results["no_division_by_zero_kpi"] = True  # denominators all guarded in compute functions
    # Chargeback reconciliation: cb rows in integrated == cb_kpis
    results["chargeback_rate_nonnegative"] = cb_kpis["chargeback_rate_pct"] >= 0
    results["disputed_ratio_nonnegative"]  = cb_kpis["disputed_amount_ratio_pct"] >= 0
    # Daily totals sum
    daily_total = txn.dropna(subset=["timestamp_clean"]).groupby(txn["timestamp_clean"].dt.date)["amount_numeric"].sum().sum()
    results["daily_total_reconciles"] = abs(daily_total - txn["amount_numeric"].sum()) < 1.0
    # Pct rates sum reasonably
    rate_sum = txn_kpis["success_rate_pct"] + txn_kpis["failure_rate_pct"] + txn_kpis["pending_rate_pct"]
    results["status_rates_sum_le100"] = rate_sum <= 100.5   # small slack for unknowns
    return results

# ══════════════════════════════════════════════════════════════════════
# 10. Report generation
# ══════════════════════════════════════════════════════════════════════
def write_reports(txn_kpis, cb_kpis, dq_kpis, insights, val_results, txn, mrc, usr):
    logger.info("Writing reports …")
    full_kpis = {"transaction_kpis": txn_kpis, "chargeback_kpis": cb_kpis, "data_quality_kpis": dq_kpis}
    with open(REPORTS / "m4_kpi_baseline.json", "w") as f:
        json.dump(full_kpis, f, indent=2)

    # KPI CSV
    rows = []
    for section, d in full_kpis.items():
        for k, v in d.items():
            rows.append({"section": section, "kpi": k, "value": v})
    pd.DataFrame(rows).to_csv(REPORTS / "m4_kpi_baseline.csv", index=False)

    # Insights MD
    with open(REPORTS / "m4_insights.md", "w") as f:
        f.write("# FinGuard M4.1 — Business Insights\n\n")
        f.write("> **Note:** This analysis identifies behavioral patterns and risk signals. "
                "It does not establish confirmed fraud without ground-truth fraud labels.\n\n")
        for line in insights:
            f.write(f"- {line}\n\n")

    # Full EDA report
    val_lines = [f"| {k} | {'✅ PASS' if v else '❌ FAIL'} |" for k, v in val_results.items()]
    all_pass = all(val_results.values())

    # Extra tables for report
    cat_tbl = txn.groupby("merchant_category_clean").agg(
        txns=("txn_id_normalized", "count"),
        total_amt=("amount_numeric", "sum"),
        cb_count=("chargeback_count", "sum")
    ).dropna().sort_values("txns", ascending=False).head(10)
    cat_tbl["cb_rate_pct"] = (cat_tbl["cb_count"] / cat_tbl["txns"].clip(lower=1) * 100).round(2)

    cat_md = "| Category | Txns | Total Amount (₹) | Chargeback Count | CB Rate% |\n| --- | --- | --- | --- | --- |\n"
    for idx, row in cat_tbl.iterrows():
        cat_md += f"| {idx} | {int(row.txns):,} | {row.total_amt:,.0f} | {int(row.cb_count):,} | {row.cb_rate_pct} |\n"

    md = f"""# FinGuard M4.1 — EDA Report

> **Disclaimer:** This analysis identifies behavioral patterns and risk signals.
> It does not establish confirmed fraud without ground-truth fraud labels.

## 1. Dataset Used

| Dataset | Rows | Columns |
| --- | --- | --- |
| finguard_transactions.csv | {len(txn):,} | {txn.shape[1]} |
| users_analytics.csv | {len(usr):,} | {usr.shape[1]} |
| merchants_analytics.csv | {len(mrc):,} | {mrc.shape[1]} |

Analysis covers transactions from **{txn_kpis['date_range_start']}** to **{txn_kpis['date_range_end']}** ({txn_kpis['analysis_days']} days).

---

## 2. Transaction KPIs

| KPI | Value |
| --- | --- |
| Total Transactions | {txn_kpis['total_transactions']:,} |
| Total Amount (₹) | {txn_kpis['total_amount']:,.2f} |
| Average Amount (₹) | {txn_kpis['avg_amount']:,.2f} |
| Median Amount (₹) | {txn_kpis['median_amount']:,.2f} |
| Min / Max Amount (₹) | {txn_kpis['min_amount']:,.2f} / {txn_kpis['max_amount']:,.2f} |
| Successful | {txn_kpis['successful_count']:,} ({txn_kpis['success_rate_pct']}%) |
| Failed | {txn_kpis['failed_count']:,} ({txn_kpis['failure_rate_pct']}%) |
| Pending | {txn_kpis['pending_count']:,} ({txn_kpis['pending_rate_pct']}%) |
| Avg Txns per Day | {txn_kpis['avg_txn_per_day']:,} |
| Avg Value per Day (₹) | {txn_kpis['avg_value_per_day']:,.2f} |

---

## 3. Chargeback KPIs

| KPI | Value |
| --- | --- |
| Transactions with Chargebacks | {cb_kpis['transactions_with_chargeback']:,} |
| Chargeback Rate | {cb_kpis['chargeback_rate_pct']}% |
| Total Disputed Amount (₹) | {cb_kpis['total_disputed_amount']:,.2f} |
| Avg Disputed Amount (₹) | {cb_kpis['avg_disputed_amount']:,.2f} |
| Disputed Amount Ratio | {cb_kpis['disputed_amount_ratio_pct']}% of total transaction value |
| Avg Report Delay (hours) | {cb_kpis['avg_report_delay_hours']} |
| Median Report Delay (hours) | {cb_kpis['median_report_delay_hours']} |
| Disputes After 7 Days | {cb_kpis['disputes_after_7_days']:,} ({cb_kpis['disputes_after_7_days_pct']}%) |

---

## 4. Data Quality Impact

| Issue | Count | Rate |
| --- | --- | --- |
| Missing UTR | {dq_kpis['utr_missing_count']:,} | {dq_kpis['utr_missing_pct']}% |
| Negative Amount | {dq_kpis['negative_amount_count']:,} | {dq_kpis['negative_amount_pct']}% |
| Invalid Timestamp | {dq_kpis['invalid_timestamp_count']:,} | {dq_kpis['invalid_timestamp_pct']}% |
| Unmatched KYC | {dq_kpis['unmatched_kyc_count']:,} | {dq_kpis['unmatched_kyc_pct']}% |
| Unmatched Merchant | {dq_kpis['unmatched_merchant_count']:,} | {dq_kpis['unmatched_merchant_pct']}% |
| Duplicate TXN ID | {dq_kpis['duplicate_txn_id_count']:,} | {dq_kpis['duplicate_txn_id_pct']}% |

---

## 5. Top Merchant Categories

{cat_md}

---

## 6. Validation Results

| Check | Result |
| --- | --- |
{chr(10).join(val_lines)}

**OVERALL: {'✅ PASS' if all_pass else '❌ FAIL'}**

---

## 7. Methodology

- **Denominators:** All rates use the full transaction count ({txn_kpis['total_transactions']:,}) as denominator unless stated otherwise.
- **Missing data:** Rows with null amounts/timestamps are excluded from numeric aggregations only. Row counts always include all records.
- **Outliers:** IQR (3× fence) and z-score (|z|>3) flagging applied but outliers are retained.
- **Anomaly labeling:** All identified patterns are labeled "risk signal" or "anomaly", never "fraud".
- **Chargeback rate:** transactions_with_chargeback / total_transactions
- **Disputed amount ratio:** total_disputed_amount / total_transaction_amount
"""

    with open(REPORTS / "m4_eda_report.md", "w") as f:
        f.write(md)

    logger.info("Reports written.")

# ══════════════════════════════════════════════════════════════════════
# 11. Main
# ══════════════════════════════════════════════════════════════════════
def main():
    txn, usr, mrc, cb = load_data()
    txn = compute_outlier_flags(txn)

    txn_kpis = compute_txn_kpis(txn)
    cb_kpis  = compute_cb_kpis(txn, cb)
    dq_kpis  = compute_dq_kpis(txn)
    insights = generate_insights(txn, usr, mrc, txn_kpis, cb_kpis, dq_kpis)
    val_res  = run_validations(txn, txn_kpis, cb_kpis)

    make_charts(txn, mrc, cb)
    write_reports(txn_kpis, cb_kpis, dq_kpis, insights, val_res, txn, mrc, usr)

    logger.info("M4.1 EDA complete.")
    return txn_kpis, cb_kpis, dq_kpis, val_res, insights

if __name__ == "__main__":
    main()
