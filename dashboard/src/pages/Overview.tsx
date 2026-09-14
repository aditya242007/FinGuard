/**
 * Overview.tsx — Executive Overview
 * All KPIs derive from filteredTransactions (computed in useFilterStore).
 * amount_numeric is the authoritative signed amount from M2/M3.
 */
import React from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';
import { AlertTriangle, TrendingUp, CheckCircle, Activity, ShieldOff, Users } from 'lucide-react';

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------
interface KpiCardProps {
  title: string;
  value: string;
  sub?: string;
  icon?: React.ReactNode;
  highlight?: 'warn' | 'danger' | 'good';
}
const KpiCard: React.FC<KpiCardProps> = ({ title, value, sub, icon, highlight }) => {
  const border =
    highlight === 'danger' ? 'border-red-800/60' :
    highlight === 'warn'   ? 'border-yellow-800/60' :
    highlight === 'good'   ? 'border-green-800/60' :
    'border-slate-700';
  return (
    <div className={`bg-slate-800 p-5 rounded-lg border ${border} flex flex-col justify-between`}>
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-slate-400 font-medium text-sm">{title}</h3>
        {icon && <div className="text-slate-500">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// DataQuality Row
// ---------------------------------------------------------------------------
const DqRow: React.FC<{label: string; count: string; pct?: string; note: string; severity: 'danger'|'warn'|'info'}> = ({label,count,pct,note,severity}) => {
  const dot =
    severity === 'danger' ? 'bg-red-500' :
    severity === 'warn'   ? 'bg-yellow-500' : 'bg-blue-500';
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-slate-700/50 last:border-0">
      <span className={`mt-1.5 shrink-0 w-2 h-2 rounded-full ${dot}`} />
      <div className="flex-1">
        <p className="text-sm text-slate-200">{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{note}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-bold text-white">{count}</p>
        {pct && <p className="text-xs text-slate-400">{pct}</p>}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Overview Page
// ---------------------------------------------------------------------------
const Overview: React.FC = () => {
  const { data, filteredTransactions } = useFilterStore();

  if (!data) return null;

  const txns = filteredTransactions;
  const n = txns.length;

  // ── Core KPIs ──────────────────────────────────────────────────────────
  // Total value = sum of signed amount_numeric (authoritative M2 field)
  const totalValue = txns.reduce((s, t) => s + (t.amount_numeric ?? 0), 0);
  const avgValue   = n > 0 ? totalValue / n : 0;

  const successCount  = txns.filter(t => t.status_clean === 'SUCCESS').length;
  const failedCount   = txns.filter(t => t.status_clean === 'FAILED').length;
  const pendingCount  = txns.filter(t => t.status_clean === 'PENDING').length;
  const successRate   = n > 0 ? successCount / n : 0;
  const failureRate   = n > 0 ? failedCount  / n : 0;
  const pendingRate   = n > 0 ? pendingCount / n : 0;

  const cbTxns      = txns.filter(t => t.has_chargeback).length;
  const cbRate      = n > 0 ? cbTxns / n : 0;
  const totalDisp   = txns.reduce((s, t) => s + (t.total_disputed_amount ?? 0), 0);
  const dispRatio   = totalValue > 0 ? totalDisp / totalValue : 0;
  const dispDelayed = txns.filter(t => t.dispute_after_7_days_flag).length;

  // ── Cluster/entity aggregates (respond to filters via txn membership) ─
  const activeMerchants = new Set(txns.map(t => t.merchant_id_normalized)).size;
  const activeUsers     = new Set(txns.map(t => t.user_id_normalized)).size;

  // Risk level breakdown (transaction-time from M6)
  const critCount  = txns.filter(t => t.transaction_time_risk_level === 'CRITICAL').length;
  const highCount  = txns.filter(t => t.transaction_time_risk_level === 'HIGH').length;
  const elevRiskN  = critCount + highCount;

  // Total clusters are global (not per-transaction)
  const clusterCount = data.clusters.length;

  // ── Data Quality (scoped to filtered transactions) ──────────────────
  const missingUtr         = txns.filter(t => t.utr_missing_flag).length;
  const negativeAmounts    = txns.filter(t => t.amount_negative_flag).length;
  const unmatchedKyc       = txns.filter(t => !t.transaction_has_kyc).length;
  const unmatchedMerchant  = txns.filter(t => !t.transaction_has_merchant).length;

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Executive Overview</h2>
        <p className="text-slate-400">
          Authoritative UPI risk intelligence — all figures derived from M3–M7 outputs.
        </p>
      </div>

      {/* ── Section 1: Transaction KPIs ──────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Transaction Metrics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard title="Total Transactions" value={formatNumber(n)} icon={<TrendingUp size={18} />} />
          <KpiCard title="Total Value" value={formatCurrency(totalValue)} icon={<Activity size={18} />} />
          <KpiCard title="Average Value" value={formatCurrency(avgValue)} />
          <KpiCard title="Success Rate" value={formatPercent(successRate)} icon={<CheckCircle size={18} className="text-green-500" />} highlight="good" />
          <KpiCard title="Failure Rate" value={formatPercent(failureRate)} icon={<AlertTriangle size={18} className="text-red-400" />} highlight="danger" />
          <KpiCard title="Pending Rate" value={formatPercent(pendingRate)} />
        </div>
      </section>

      {/* ── Section 2: Risk & Chargeback KPIs ───────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Risk &amp; Chargeback
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard
            title="Chargeback Rate"
            value={formatPercent(cbRate)}
            sub="Distinct txns with ≥1 chargeback / total"
            icon={<AlertTriangle size={18} className="text-red-500" />}
            highlight="danger"
          />
          <KpiCard title="Chargebacked Txns" value={formatNumber(cbTxns)} />
          <KpiCard title="Disputed Amount" value={formatCurrency(totalDisp)} highlight="warn" />
          <KpiCard
            title="Disputed Amount Ratio"
            value={formatPercent(dispRatio)}
            sub="Disputed / Total transaction value"
          />
          <KpiCard
            title="Late Disputes (>7d)"
            value={formatNumber(dispDelayed)}
            sub="Reported after 7 days"
            highlight="warn"
          />
          <KpiCard
            title="Elevated-Risk Txns"
            value={formatNumber(elevRiskN)}
            sub={`CRITICAL: ${critCount} | HIGH: ${highCount} (transaction-time risk, M6)`}
            highlight={elevRiskN > 0 ? 'warn' : undefined}
          />
        </div>
      </section>

      {/* ── Section 3: Entity & Cluster KPIs ────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Entity Intelligence
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard title="Active Users" value={formatNumber(activeUsers)} icon={<Users size={18} />} />
          <KpiCard title="Active Merchants" value={formatNumber(activeMerchants)} />
          <KpiCard
            title="Investigation Clusters"
            value={formatNumber(clusterCount)}
            sub="M7 suspicious clusters (global — not filter-scoped)"
          />
          <KpiCard
            title="High/Critical Merchants"
            value={formatNumber(
              data.merchants.filter(m => m.risk_level === 'HIGH' || m.risk_level === 'CRITICAL').length
            )}
            sub="Retrospective risk level from M6"
            highlight="warn"
          />
        </div>
      </section>

      {/* ── Section 4: Data Quality ──────────────────────────────────────── */}
      <section>
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
          <h3 className="font-semibold text-base mb-1 flex items-center gap-2">
            <ShieldOff size={16} className="text-yellow-500" />
            Data Quality Snapshot
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Scoped to currently filtered transactions ({formatNumber(n)} rows).
            These figures represent real data quality issues from M1–M2.
          </p>
          <DqRow
            label="Unmatched KYC"
            count={formatNumber(unmatchedKyc)}
            pct={formatPercent(unmatchedKyc / (n || 1))}
            note="No KYC record found — limits identity-based interpretation"
            severity="danger"
          />
          <DqRow
            label="Unmatched Merchant"
            count={formatNumber(unmatchedMerchant)}
            pct={formatPercent(unmatchedMerchant / (n || 1))}
            note="No merchant record found — category and risk context unavailable"
            severity="danger"
          />
          <DqRow
            label="Missing UTR"
            count={formatNumber(missingUtr)}
            pct={formatPercent(missingUtr / (n || 1))}
            note="Unique Transaction Reference absent — traceability gap"
            severity="warn"
          />
          <DqRow
            label="Negative Amounts"
            count={formatNumber(negativeAmounts)}
            pct={formatPercent(negativeAmounts / (n || 1))}
            note="Reversal or anomalous entry — included in total value (not silently dropped)"
            severity="warn"
          />
        </div>
      </section>
    </div>
  );
};

export default Overview;
