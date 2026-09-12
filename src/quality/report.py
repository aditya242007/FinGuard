"""
src/quality/report.py
---------------------
Report generator for the FinGuard data quality audit.

Produces:
  reports/data_quality_report.json   — full machine-readable audit results
  reports/data_quality_report.md     — human-readable markdown report

Design:
- Severity is assigned per-issue type, not per-row count.
  Severity levels: CRITICAL / HIGH / MEDIUM / LOW
- Every issue entry includes: issue_name, count, percentage (if applicable),
  severity, and recommended_action.
- No hardcoded row counts. All counts come from the audit dict.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity thresholds (percentage-based, used for certain issue types)
# ---------------------------------------------------------------------------
_PCT_CRITICAL  = 20.0
_PCT_HIGH      = 10.0
_PCT_MEDIUM    = 5.0


def _pct_severity(pct: float) -> str:
    if pct >= _PCT_CRITICAL:
        return "CRITICAL"
    if pct >= _PCT_HIGH:
        return "HIGH"
    if pct >= _PCT_MEDIUM:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Issue builder helpers
# ---------------------------------------------------------------------------

def _issue(
    name: str,
    count: int,
    pct: float | None,
    severity: str,
    action: str,
) -> dict[str, Any]:
    return {
        "issue_name": name,
        "count": count,
        "percentage": pct,
        "severity": severity,
        "recommended_action": action,
    }


def _safe_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Per-section issue extractors
# ---------------------------------------------------------------------------

def _extract_transaction_issues(
    txn_profile: dict, txn_issues: dict
) -> list[dict]:
    total = txn_profile.get("row_count", 1) or 1
    out: list[dict] = []

    dup = txn_issues.get("duplicate_txn_id", {})
    c = _safe_int(dup.get("count", 0))
    out.append(_issue(
        "Duplicate transaction IDs (txn_id)",
        c, round(c / total * 100, 2),
        "HIGH" if c > 0 else "LOW",
        "Investigate duplicates; during cleaning retain the earliest record "
        "or flag all as a ring-pattern if amounts differ.",
    ))

    dup_row = _safe_int(txn_issues.get("duplicate_complete_rows", {}).get("count", 0))
    out.append(_issue(
        "Exact duplicate transaction rows",
        dup_row, round(dup_row / total * 100, 2),
        "MEDIUM" if dup_row > 0 else "LOW",
        "Deduplicate exact rows in cleaning phase; keep one copy.",
    ))

    for field in ["txn_id", "user_id", "merchant_id", "utr"]:
        key = f"blank_{field}"
        info = txn_issues.get(key, {})
        c = _safe_int(info.get("count", 0))
        pct = _safe_float(info.get("pct", 0.0))
        out.append(_issue(
            f"Blank {field}",
            c, pct,
            _pct_severity(pct) if c > 0 else "LOW",
            f"Records with blank {field} cannot be joined or traced. "
            "Flag for quarantine review in Milestone 2.",
        ))

    amt = txn_issues.get("amount_anomalies", {})
    for sub_key, sev, action in [
        ("blank_count",    "CRITICAL",
         "Transactions with no amount are unusable; quarantine after review."),
        ("malformed_count","HIGH",
         "Strip currency symbols (Rs., ₹, INR) and parse to float in cleaning."),
        ("negative_count", "HIGH",
         "Negative amounts may represent reversals; flag and verify with status."),
        ("zero_count",     "MEDIUM",
         "Zero-amount transactions may be test rows; verify with merchant."),
    ]:
        c = _safe_int(amt.get(sub_key, 0))
        out.append(_issue(
            f"Amount — {sub_key.replace('_count','')}",
            c, round(c / total * 100, 2),
            sev if c > 0 else "LOW",
            action,
        ))

    ts = txn_issues.get("timestamp_anomalies", {})
    for ts_key, sev, action in [
        ("unix_epoch", "HIGH",
         "Convert Unix epoch timestamps to ISO-8601 datetime in cleaning."),
        ("unparseable","CRITICAL",
         "Rows with unparseable timestamps cannot be time-series analysed; quarantine."),
        ("blank",      "HIGH",
         "Missing timestamps make time-series analysis impossible; quarantine."),
    ]:
        c = _safe_int(ts.get(ts_key, 0))
        out.append(_issue(
            f"Timestamp — {ts_key}",
            c, round(c / total * 100, 2),
            sev if c > 0 else "LOW",
            action,
        ))

    mcc = txn_issues.get("mcc_format", {})
    unusual_c = _safe_int(mcc.get("counts", {}).get("unusual", 0))
    lz_c      = _safe_int(mcc.get("counts", {}).get("leading_zero", 0))
    out.append(_issue(
        "Unusual MCC format",
        unusual_c, round(unusual_c / total * 100, 2),
        "HIGH" if unusual_c > 0 else "LOW",
        "Normalise MCC to 4-digit numeric string; map MCC-XXXX prefix variants.",
    ))
    out.append(_issue(
        "MCC with leading zero (5-digit)",
        lz_c, round(lz_c / total * 100, 2),
        "MEDIUM" if lz_c > 0 else "LOW",
        "Strip leading zero to standardise to 4-digit MCC.",
    ))

    return out


def _extract_kyc_issues(kyc_profile: dict, kyc_issues: dict) -> list[dict]:
    total = kyc_profile.get("row_count", 1) or 1
    out: list[dict] = []

    dup_norm = _safe_int(kyc_issues.get("duplicate_user_id_normalised", {}).get("count", 0))
    out.append(_issue(
        "Duplicate user IDs (normalised)",
        dup_norm, round(dup_norm / total * 100, 2),
        "CRITICAL" if dup_norm > 0 else "LOW",
        "Normalise user_id format and deduplicate; merge or flag duplicates.",
    ))

    dup_row = _safe_int(kyc_issues.get("duplicate_complete_rows", {}).get("count", 0))
    out.append(_issue(
        "Exact duplicate KYC rows",
        dup_row, round(dup_row / total * 100, 2),
        "MEDIUM" if dup_row > 0 else "LOW",
        "Remove exact duplicate rows in cleaning.",
    ))

    for field in ["pan", "aadhaar", "date_of_birth", "monthly_income", "signup_timestamp"]:
        key = f"blank_{field}"
        info = kyc_issues.get(key, {})
        c = _safe_int(info.get("count", 0))
        pct = _safe_float(info.get("pct", 0.0))
        out.append(_issue(
            f"Blank {field}",
            c, pct,
            _pct_severity(pct) if c > 0 else "LOW",
            f"Missing {field} is a KYC compliance risk; flag records for manual review.",
        ))

    # Status inconsistency
    ks_dist = kyc_issues.get("kyc_status_distribution", {})
    n_unique_raw = len(ks_dist)
    ks_norm = kyc_issues.get("kyc_status_unique_normalised", [])
    n_unique_norm = len(ks_norm)
    inconsistent_c = sum(v for k, v in ks_dist.items() if k != k.upper()) \
        if ks_dist else 0
    out.append(_issue(
        f"Inconsistent KYC status casing ({n_unique_raw} raw variants → "
        f"{n_unique_norm} normalised)",
        inconsistent_c, round(inconsistent_c / total * 100, 2),
        "MEDIUM" if n_unique_raw > n_unique_norm else "LOW",
        "Normalise kyc_status to uppercase canonical values (e.g., VERIFIED, PENDING, REJECTED).",
    ))

    rs_dist = kyc_issues.get("risk_segment_distribution", {})
    n_rs_raw = len(rs_dist)
    rs_norm = kyc_issues.get("risk_segment_unique_normalised", [])
    n_rs_norm = len(rs_norm)
    rs_incon = sum(v for k, v in rs_dist.items() if k != k.upper()) if rs_dist else 0
    out.append(_issue(
        f"Inconsistent risk_segment casing ({n_rs_raw} raw variants)",
        rs_incon, round(rs_incon / total * 100, 2),
        "MEDIUM" if n_rs_raw > n_rs_norm else "LOW",
        "Normalise risk_segment to uppercase (HIGH, MEDIUM, LOW).",
    ))

    for field in ["city", "state"]:
        info = kyc_issues.get(f"{field}_capitalisation_inconsistencies", {})
        c = _safe_int(info.get("inconsistent_count", 0))
        tot_nb = _safe_int(info.get("total_non_blank", 1)) or 1
        out.append(_issue(
            f"{field.title()} capitalisation inconsistencies",
            c, round(c / tot_nb * 100, 2),
            "LOW",
            f"Title-case {field} during cleaning.",
        ))

    sym = kyc_issues.get("income_with_symbols", {})
    c = _safe_int(sym.get("count", 0))
    out.append(_issue(
        "Monthly income with currency symbol / k-suffix",
        c, round(c / total * 100, 2),
        "MEDIUM" if c > 0 else "LOW",
        "Strip ₹, INR, Rs. and expand 'k' suffix; store as numeric.",
    ))

    inc = kyc_issues.get("income_anomalies", {})
    mal_c = _safe_int(inc.get("malformed_count", 0))
    out.append(_issue(
        "Malformed monthly income (unparseable after symbol strip)",
        mal_c, round(mal_c / total * 100, 2),
        "HIGH" if mal_c > 0 else "LOW",
        "Manually review unparseable incomes; quarantine if unrecoverable.",
    ))

    return out


def _extract_merchant_issues(merch_profile: dict, merch_issues: dict) -> list[dict]:
    total = merch_profile.get("row_count", 1) or 1
    out: list[dict] = []

    dup_norm = _safe_int(merch_issues.get("duplicate_merchant_id_normalised", {}).get("count", 0))
    out.append(_issue(
        "Duplicate merchant IDs (normalised)",
        dup_norm, round(dup_norm / total * 100, 2),
        "CRITICAL" if dup_norm > 0 else "LOW",
        "Normalise merchant_id format and deduplicate; retain most recent record.",
    ))

    dup_row = _safe_int(merch_issues.get("duplicate_complete_rows", {}).get("count", 0))
    out.append(_issue(
        "Exact duplicate merchant rows",
        dup_row, round(dup_row / total * 100, 2),
        "MEDIUM" if dup_row > 0 else "LOW",
        "Remove exact duplicate rows.",
    ))

    blank_mcc = merch_issues.get("blank_mcc", {})
    c = _safe_int(blank_mcc.get("count", 0))
    pct = _safe_float(blank_mcc.get("pct", 0.0))
    out.append(_issue(
        "Blank MCC code",
        c, pct,
        _pct_severity(pct) if c > 0 else "LOW",
        "MCC is required for regulatory category mapping; impute from merchant_category if possible.",
    ))

    mcc_fmt = merch_issues.get("mcc_format", {})
    for fmt_key, sev, action in [
        ("unusual",      "HIGH",   "Map non-standard MCC formats to 4-digit standard."),
        ("dashed_prefix","MEDIUM", "Strip 'MCC-' prefix; retain 4-digit code."),
        ("leading_zero", "MEDIUM", "Strip leading zero from 5-digit MCC."),
    ]:
        c = _safe_int(mcc_fmt.get("counts", {}).get(fmt_key, 0))
        out.append(_issue(
            f"MCC format — {fmt_key}",
            c, round(c / total * 100, 2),
            sev if c > 0 else "LOW",
            action,
        ))

    blank_ob = merch_issues.get("blank_onboarding_date", {})
    c = _safe_int(blank_ob.get("count", 0))
    pct = _safe_float(blank_ob.get("pct", 0.0))
    out.append(_issue(
        "Missing onboarding date",
        c, pct,
        "MEDIUM" if c > 0 else "LOW",
        "Onboarding date is required for merchant age analysis; flag for manual lookup.",
    ))

    blank_sa = merch_issues.get("blank_or_invalid_settlement_account", {})
    c = _safe_int(blank_sa.get("count", 0))
    pct = _safe_float(blank_sa.get("pct", 0.0))
    out.append(_issue(
        "Blank or invalid settlement account",
        c, pct,
        "HIGH" if c > 0 else "LOW",
        "Missing settlement account blocks payment; flag as HIGH risk.",
    ))

    for field in ["merchant_category", "merchant_status", "business_type"]:
        dist = merch_issues.get(f"{field}_distribution", {})
        n_raw = len(dist)
        normalised = {k.strip().upper(): v for k, v in dist.items()}
        n_norm = len(normalised)
        if n_raw > n_norm:
            incon_c = sum(v for k, v in dist.items() if k != k.strip().upper())
            out.append(_issue(
                f"Inconsistent {field} variants ({n_raw} raw → {n_norm} normalised)",
                incon_c, round(incon_c / total * 100, 2),
                "MEDIUM",
                f"Standardise {field} to a controlled vocabulary.",
            ))

    tick = merch_issues.get("ticket_size_anomalies", {})
    for sub_key, sev, action in [
        ("negative_count","HIGH",   "Negative ticket sizes are invalid; verify or quarantine."),
        ("malformed_count","MEDIUM","Strip INR/₹ prefix; convert to numeric."),
    ]:
        c = _safe_int(tick.get(sub_key, 0))
        out.append(_issue(
            f"Ticket size — {sub_key.replace('_count','')}",
            c, round(c / total * 100, 2),
            sev if c > 0 else "LOW",
            action,
        ))

    return out


def _extract_chargeback_issues(cb_profile: dict, cb_issues: dict) -> list[dict]:
    total = cb_profile.get("row_count", 1) or 1
    out: list[dict] = []

    for check_key, issue_name, sev, action in [
        ("duplicate_complaint_id", "Duplicate complaint IDs",
         "CRITICAL", "Investigate duplicate complaint IDs; may indicate system re-submission."),
        ("duplicate_txn_id",       "Duplicate txn_id in chargebacks",
         "HIGH",     "Multiple chargebacks on same txn may indicate double-dispute; review."),
        ("duplicate_complete_rows","Exact duplicate chargeback rows",
         "MEDIUM",   "Remove exact duplicates in cleaning."),
    ]:
        info = cb_issues.get(check_key, {})
        c = _safe_int(info.get("count", 0))
        out.append(_issue(
            issue_name, c, round(c / total * 100, 2),
            sev if c > 0 else "LOW", action,
        ))

    btxn = cb_issues.get("blank_txn_id", {})
    c = _safe_int(btxn.get("count", 0))
    pct = _safe_float(btxn.get("pct", 0.0))
    out.append(_issue(
        "Blank txn_id in chargebacks",
        c, pct,
        _pct_severity(pct) if c > 0 else "LOW",
        "Chargebacks without txn_id cannot be linked to transactions; flag for manual review.",
    ))

    da = cb_issues.get("disputed_amount_anomalies", {})
    for sub_key, sev, action in [
        ("blank_count",    "HIGH",   "Blank disputed amount makes financial impact assessment impossible."),
        ("malformed_count","MEDIUM", "Strip symbols and parse to float."),
        ("negative_count", "MEDIUM", "Negative disputed amounts need verification."),
    ]:
        c = _safe_int(da.get(sub_key, 0))
        out.append(_issue(
            f"Disputed amount — {sub_key.replace('_count','')}",
            c, round(c / total * 100, 2),
            sev if c > 0 else "LOW", action,
        ))

    for field in ["reason_code", "resolution_status", "severity", "channel"]:
        dist = cb_issues.get(f"{field}_distribution", {})
        n_raw = len(dist)
        n_norm = len({k.strip().upper() for k in dist})
        if n_raw > n_norm:
            incon_c = sum(v for k, v in dist.items() if k != k.strip().upper())
            out.append(_issue(
                f"Inconsistent {field} variants ({n_raw} raw → {n_norm} normalised)",
                incon_c, round(incon_c / total * 100, 2),
                "MEDIUM",
                f"Standardise {field} to canonical uppercase vocabulary.",
            ))

    for ts_field in ["transaction_timestamp", "reported_timestamp", "bank_response_timestamp"]:
        key = f"{ts_field}_anomalies"
        ts = cb_issues.get(key, {})
        for ts_sub, sev, action in [
            ("unix_epoch", "HIGH",    "Convert Unix epoch to ISO-8601."),
            ("unparseable","CRITICAL","Rows with unparseable timestamps cannot be timed; quarantine."),
            ("blank",      "HIGH",    "Missing timestamps break dispute delay analysis."),
        ]:
            c = _safe_int(ts.get(ts_sub, 0))
            if c > 0:
                out.append(_issue(
                    f"{ts_field} — {ts_sub}",
                    c, round(c / total * 100, 2),
                    sev, action,
                ))

    return out


def _extract_integrity_issues(
    integrity: dict,
    txn_total: int,
    cb_total: int,
) -> list[dict]:
    out: list[dict] = []
    for key, label, ref_total, sev_fn, action in [
        ("txn_user_not_in_kyc",
         "Transaction user_id not found in KYC (normalised)",
         txn_total,
         lambda p: "CRITICAL" if p >= 20 else "HIGH" if p >= 5 else "MEDIUM",
         "Normalise user_id format and re-attempt join before flagging as orphan."),
        ("txn_merchant_not_in_master",
         "Transaction merchant_id not found in Merchant master (normalised)",
         txn_total,
         lambda p: "HIGH" if p >= 10 else "MEDIUM",
         "Normalise merchant_id format; orphan transactions cannot be risk-scored."),
        ("cb_txn_not_in_transactions",
         "Chargeback txn_id not found in Transactions (normalised)",
         cb_total,
         lambda p: "HIGH" if p >= 10 else "MEDIUM",
         "Normalise txn_id; unlinked chargebacks cannot contribute to dispute ratio."),
        ("cb_user_not_in_kyc",
         "Chargeback user_id not found in KYC (normalised)",
         cb_total,
         lambda p: "HIGH" if p >= 10 else "MEDIUM",
         "Normalise user_id; unlinked chargebacks cannot be attributed to a KYC profile."),
        ("cb_merchant_not_in_master",
         "Chargeback merchant_id not found in Merchant master (normalised)",
         cb_total,
         lambda p: "HIGH" if p >= 10 else "MEDIUM",
         "Normalise merchant_id; unlinked chargebacks inflate unattributed dispute count."),
    ]:
        info = integrity.get(key, {})
        c = _safe_int(info.get("unmatched_count", 0))
        pct = _safe_float(info.get("unmatched_pct", 0.0))
        out.append(_issue(
            label, c, pct,
            sev_fn(pct) if c > 0 else "LOW",
            action,
        ))
    return out


def _severity_counts(issues: list[dict]) -> dict[str, int]:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for i in issues:
        sev = i.get("severity", "LOW")
        counts[sev] = counts.get(sev, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# JSON report writer
# ---------------------------------------------------------------------------

def write_json_report(audit_result: dict, reports_dir: Path) -> Path:
    """Write the full audit result dict to JSON."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "data_quality_report.json"

    class _Encoder(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            if hasattr(o, "item"):  # numpy scalar
                return o.item()
            return super().default(o)

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(audit_result, fh, indent=2, ensure_ascii=False, cls=_Encoder)

    logger.info("JSON report written to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    sep = " | ".join(["---"] * len(headers))
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "| " + sep + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def _issues_table(issues: list[dict]) -> str:
    headers = ["Issue", "Count", "Percentage", "Severity", "Recommended Action"]
    rows = [
        [
            i["issue_name"],
            i["count"],
            f"{i['percentage']:.2f}%" if i.get("percentage") is not None else "—",
            i["severity"],
            i["recommended_action"],
        ]
        for i in issues
    ]
    return _md_table(headers, rows)


def write_markdown_report(
    audit_result: dict,
    all_issues: dict[str, list[dict]],
    reports_dir: Path,
) -> Path:
    """Write the human-readable markdown quality report."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "data_quality_report.md"

    txn_p   = audit_result["transactions"]["profile"]
    kyc_p   = audit_result["kyc"]["profile"]
    merch_p = audit_result["merchants"]["profile"]
    cb_p    = audit_result["chargebacks"]["profile"]

    all_issue_list: list[dict] = []
    for section_issues in all_issues.values():
        all_issue_list.extend(section_issues)

    sev_total = _severity_counts(all_issue_list)
    non_low   = [i for i in all_issue_list if i["severity"] != "LOW" and i["count"] > 0]
    critical  = [i for i in all_issue_list if i["severity"] == "CRITICAL" and i["count"] > 0]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Header
    lines += [
        "# FinGuard Data Quality Report",
        "",
        f"_Generated: {generated_at}_",
        "",
    ]

    # -----------------------------------------------------------------------
    # Executive Summary
    lines += [
        "## Executive Summary",
        "",
        "This report summarises the data quality audit for four raw datasets "
        "ingested into the FinGuard pipeline. **No data has been modified or "
        "deleted.** All findings are observations only.",
        "",
        f"- **Total issues detected:** {len(non_low)}",
        f"- **CRITICAL:** {sev_total['CRITICAL']}",
        f"- **HIGH:** {sev_total['HIGH']}",
        f"- **MEDIUM:** {sev_total['MEDIUM']}",
        f"- **LOW:** {sev_total['LOW']}",
        "",
    ]

    if critical:
        lines.append("### ⚠️ Critical Issues Requiring Immediate Attention")
        lines.append("")
        for i in critical:
            lines.append(f"- **{i['issue_name']}** — {i['count']} records")
        lines.append("")

    # -----------------------------------------------------------------------
    # Dataset Overview
    lines += [
        "## Dataset Overview",
        "",
        _md_table(
            ["Dataset", "Rows", "Columns", "Duplicate Rows"],
            [
                ["Transactions",  txn_p["row_count"],   txn_p["column_count"],   txn_p["duplicate_row_count"]],
                ["KYC Records",   kyc_p["row_count"],   kyc_p["column_count"],   kyc_p["duplicate_row_count"]],
                ["Merchants",     merch_p["row_count"], merch_p["column_count"], merch_p["duplicate_row_count"]],
                ["Chargebacks",   cb_p["row_count"],    cb_p["column_count"],    cb_p["duplicate_row_count"]],
            ],
        ),
        "",
    ]

    # -----------------------------------------------------------------------
    # Missing value summary tables per dataset
    def _missing_table(profile: dict) -> str:
        mv = profile.get("missing_values", [])
        rows_sorted = sorted(mv, key=lambda r: r["missing_count"], reverse=True)
        headers = ["Column", "Missing Count", "Missing %", "Unique Values", "Sample"]
        rows = [
            [
                r["column"],
                r["missing_count"],
                f"{r['missing_pct']:.2f}%",
                r["unique_count"],
                ", ".join(r["sample_values"][:3]),
            ]
            for r in rows_sorted
        ]
        return _md_table(headers, rows)

    # -----------------------------------------------------------------------
    # Transaction Quality
    lines += [
        "## Transaction Quality",
        "",
        "### Missing Values",
        "",
        _missing_table(txn_p),
        "",
        "### Detected Issues",
        "",
        _issues_table(all_issues.get("transactions", [])),
        "",
        "### Status Distribution",
        "",
    ]
    status_dist = audit_result["transactions"]["issues"].get("status_distribution", {})
    if status_dist:
        lines.append(_md_table(
            ["Status Value", "Count"],
            [[k, v] for k, v in sorted(status_dist.items(), key=lambda x: -x[1])],
        ))
    lines.append("")

    # -----------------------------------------------------------------------
    # KYC Quality
    lines += [
        "## KYC Quality",
        "",
        "### Missing Values",
        "",
        _missing_table(kyc_p),
        "",
        "### Detected Issues",
        "",
        _issues_table(all_issues.get("kyc", [])),
        "",
        "### KYC Status Distribution",
        "",
    ]
    ks_dist = audit_result["kyc"]["issues"].get("kyc_status_distribution", {})
    if ks_dist:
        lines.append(_md_table(
            ["KYC Status", "Count"],
            [[k, v] for k, v in sorted(ks_dist.items(), key=lambda x: -x[1])],
        ))
    lines.append("")

    # -----------------------------------------------------------------------
    # Merchant Quality
    lines += [
        "## Merchant Quality",
        "",
        "### Missing Values",
        "",
        _missing_table(merch_p),
        "",
        "### Detected Issues",
        "",
        _issues_table(all_issues.get("merchants", [])),
        "",
    ]

    # -----------------------------------------------------------------------
    # Chargeback Quality
    lines += [
        "## Chargeback Quality",
        "",
        "### Missing Values",
        "",
        _missing_table(cb_p),
        "",
        "### Detected Issues",
        "",
        _issues_table(all_issues.get("chargebacks", [])),
        "",
        "### Severity Distribution",
        "",
    ]
    sev_dist = audit_result["chargebacks"]["issues"].get("severity_distribution", {})
    if sev_dist:
        lines.append(_md_table(
            ["Severity Value", "Count"],
            [[k, v] for k, v in sorted(sev_dist.items(), key=lambda x: -x[1])],
        ))
    lines.append("")

    # -----------------------------------------------------------------------
    # Referential Integrity
    lines += [
        "## Referential Integrity",
        "",
        _issues_table(all_issues.get("referential_integrity", [])),
        "",
    ]

    # -----------------------------------------------------------------------
    # Critical Data Risks
    lines += [
        "## Critical Data Risks",
        "",
        "The following risk factors could materially affect downstream analytics "
        "if not addressed before the cleaning phase:",
        "",
    ]
    high_and_critical = [
        i for i in all_issue_list
        if i["severity"] in ("CRITICAL", "HIGH") and i["count"] > 0
    ]
    if high_and_critical:
        for i in high_and_critical:
            lines.append(
                f"- **[{i['severity']}]** {i['issue_name']}: "
                f"{i['count']} records ({i.get('percentage', 0):.2f}%)"
            )
    else:
        lines.append("_No CRITICAL or HIGH issues detected._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Recommended Cleaning Actions
    lines += [
        "## Recommended Cleaning Actions",
        "",
        "These actions are recommended for Milestone 2 (Cleaning). "
        "**Do not apply any changes to raw files.**",
        "",
    ]
    priority_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    for sev in priority_order:
        group = [i for i in all_issue_list if i["severity"] == sev and i["count"] > 0]
        if group:
            lines.append(f"### {sev} Priority")
            lines.append("")
            for i in group:
                lines.append(f"1. **{i['issue_name']}** — {i['recommended_action']}")
            lines.append("")

    lines += [
        "---",
        "_FinGuard Milestone 1 — Audit Only. No records were modified or deleted._",
    ]

    with out_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    logger.info("Markdown report written to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------

def generate_reports(audit_result: dict, reports_dir: Path) -> tuple[Path, Path]:
    """Generate both JSON and Markdown reports from an audit result dict.

    Parameters
    ----------
    audit_result : dict
        The structured dict returned by ``run_full_audit()``.
    reports_dir : Path
        Directory where reports will be written.

    Returns
    -------
    tuple[Path, Path]
        (json_path, markdown_path)
    """
    txn_total = audit_result["transactions"]["profile"].get("row_count", 1) or 1
    cb_total  = audit_result["chargebacks"]["profile"].get("row_count", 1) or 1

    all_issues: dict[str, list[dict]] = {
        "transactions": _extract_transaction_issues(
            audit_result["transactions"]["profile"],
            audit_result["transactions"]["issues"],
        ),
        "kyc": _extract_kyc_issues(
            audit_result["kyc"]["profile"],
            audit_result["kyc"]["issues"],
        ),
        "merchants": _extract_merchant_issues(
            audit_result["merchants"]["profile"],
            audit_result["merchants"]["issues"],
        ),
        "chargebacks": _extract_chargeback_issues(
            audit_result["chargebacks"]["profile"],
            audit_result["chargebacks"]["issues"],
        ),
        "referential_integrity": _extract_integrity_issues(
            audit_result["referential_integrity"],
            txn_total,
            cb_total,
        ),
    }

    # Embed extracted issues into audit_result for JSON
    audit_result["extracted_issues"] = {k: v for k, v in all_issues.items()}

    json_path = write_json_report(audit_result, reports_dir)
    md_path   = write_markdown_report(audit_result, all_issues, reports_dir)

    return json_path, md_path
