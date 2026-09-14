/**
 * RiskIntelligence.tsx — Fraud & Risk Intelligence
 * Shows investigation-candidate clusters and top-risk merchants.
 * Applies global filters to merchant/transaction data.
 * Never uses fraud-probability language; uses M6 risk-score semantics.
 */
import React, { useMemo, useState } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';
import { ShieldAlert, AlertTriangle, ChevronDown, ChevronUp, Info } from 'lucide-react';

// ---------------------------------------------------------------------------
// Risk badge
// ---------------------------------------------------------------------------
const RiskBadge: React.FC<{ level?: string }> = ({ level }) => {
  const cls =
    level === 'CRITICAL' ? 'bg-red-900/70 text-red-200 border-red-700' :
    level === 'HIGH'     ? 'bg-orange-900/70 text-orange-200 border-orange-700' :
    level === 'MEDIUM'   ? 'bg-yellow-900/70 text-yellow-200 border-yellow-700' :
    level === 'LOW'      ? 'bg-green-900/70 text-green-200 border-green-700' :
    'bg-slate-800 text-slate-300 border-slate-700';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${cls}`}>
      {level ?? 'UNKNOWN'}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Expandable explanation row
// ---------------------------------------------------------------------------
const ExplanationRow: React.FC<{ explanation: string; signals: string[] }> = ({ explanation, signals }) => {
  const [open, setOpen] = useState(false);
  const validSignals = signals.filter(Boolean);
  if (!explanation && validSignals.length === 0) return null;
  return (
    <tr>
      <td colSpan={9} className="px-4 pb-3 pt-0">
        <button
          onClick={() => setOpen(o => !o)}
          className="text-xs text-blue-400 hover:text-blue-200 flex items-center gap-1"
        >
          <Info size={11} /> {open ? 'Hide' : 'Show'} behavioral risk signals
          {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>
        {open && (
          <div className="mt-2 bg-slate-900/50 border border-slate-700 rounded p-3 text-xs text-slate-400">
            {validSignals.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {validSignals.map(s => (
                  <span key={s} className="bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-slate-300">
                    {s}
                  </span>
                ))}
              </div>
            )}
            {explanation && <p className="text-slate-500">{explanation}</p>}
          </div>
        )}
      </td>
    </tr>
  );
};

// ---------------------------------------------------------------------------
// RiskIntelligence
// ---------------------------------------------------------------------------
const PAGE_SIZE = 20;

const RiskIntelligence: React.FC = () => {
  const { data, filteredTransactions, merchantCategory, riskLevel } = useFilterStore();
  const [clusterPage, setClusterPage] = useState(0);
  const [merchantPage, setMerchantPage] = useState(0);

  if (!data) return null;

  // ── Cluster view (always shows all 655 from M7, sorted by risk score) ──
  const sortedClusters = useMemo(() =>
    [...data.clusters].sort((a, b) => b.cluster_risk_score - a.cluster_risk_score),
    [data.clusters]
  );
  const clusterPageData = sortedClusters.slice(clusterPage * PAGE_SIZE, (clusterPage + 1) * PAGE_SIZE);
  const clusterPages = Math.ceil(sortedClusters.length / PAGE_SIZE);

  // ── Merchant view (scoped to global filter: category + riskLevel) ──────
  const filteredMerchantIds = useMemo(() => {
    const ids = new Set(filteredTransactions.map(t => t.merchant_id_normalized));
    return ids;
  }, [filteredTransactions]);

  const filteredMerchants = useMemo(() => {
    return data.merchants
      .filter(m => {
        if (!filteredMerchantIds.has(m.merchant_id_normalized)) return false;
        if (merchantCategory && m.merchant_category_clean !== merchantCategory) return false;
        if (riskLevel && m.risk_level !== riskLevel) return false;
        return true;
      })
      .sort((a, b) => (b.retrospective_risk_score ?? 0) - (a.retrospective_risk_score ?? 0));
  }, [data.merchants, filteredMerchantIds, merchantCategory, riskLevel]);

  const merchantPageData = filteredMerchants.slice(merchantPage * PAGE_SIZE, (merchantPage + 1) * PAGE_SIZE);
  const merchantPages = Math.ceil(filteredMerchants.length / PAGE_SIZE);

  // ── Summary counts ────────────────────────────────────────────────────
  const critClusters = sortedClusters.filter(c => c.risk_level === 'CRITICAL').length;
  const highClusters = sortedClusters.filter(c => c.risk_level === 'HIGH').length;
  const critMerchants = filteredMerchants.filter(m => m.risk_level === 'CRITICAL').length;
  const highMerchants = filteredMerchants.filter(m => m.risk_level === 'HIGH').length;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Fraud &amp; Risk Intelligence</h2>
        <p className="text-slate-400">
          Investigation candidates — elevated behavioral risk signals from M6 &amp; M7 outputs.
          Risk scores are not fraud probability; they represent behavioral risk signals.
        </p>
      </div>

      {/* ── Cluster Summary ──────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <ShieldAlert className="text-orange-500" />
            Investigation-Candidate Clusters ({formatNumber(sortedClusters.length)})
          </h3>
          <div className="text-xs text-slate-500">
            <span className="text-red-400 font-semibold">{critClusters}</span> CRITICAL ·{' '}
            <span className="text-orange-400 font-semibold">{highClusters}</span> HIGH
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
              <tr>
                <th className="p-3">Cluster ID</th>
                <th className="p-3">Risk Level</th>
                <th className="p-3">Score</th>
                <th className="p-3">Users</th>
                <th className="p-3">Merchants</th>
                <th className="p-3">Txns</th>
                <th className="p-3">CB Rate</th>
                <th className="p-3">CB Records</th>
                <th className="p-3 min-w-[220px]">Top Signals</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {clusterPageData.map(c => (
                <React.Fragment key={c.cluster_id}>
                  <tr className="hover:bg-slate-700/30 transition-colors">
                    <td className="p-3 font-mono font-medium">{c.cluster_id}</td>
                    <td className="p-3"><RiskBadge level={c.risk_level} /></td>
                    <td className="p-3 font-bold">{c.cluster_risk_score.toFixed(1)}</td>
                    <td className="p-3">{c.n_users}</td>
                    <td className="p-3">{c.n_merchants}</td>
                    <td className="p-3">{c.n_transactions}</td>
                    <td className="p-3 text-red-400">{formatPercent(c.cluster_chargeback_rate)}</td>
                    <td className="p-3 text-slate-400">{c.chargeback_count}</td>
                    <td className="p-3 text-xs text-slate-400 whitespace-normal">
                      {c.top_signals.split('|').filter(Boolean).join(' · ')}
                    </td>
                  </tr>
                  <ExplanationRow
                    explanation={c.explanation}
                    signals={c.top_signals.split('|').filter(Boolean)}
                  />
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
          <span>Page {clusterPage + 1} of {clusterPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setClusterPage(p => Math.max(0, p - 1))}
              disabled={clusterPage === 0}
              className="px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            >← Prev</button>
            <button
              onClick={() => setClusterPage(p => Math.min(clusterPages - 1, p + 1))}
              disabled={clusterPage === clusterPages - 1}
              className="px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            >Next →</button>
          </div>
        </div>
      </section>

      {/* ── Merchant Risk Table ─────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <AlertTriangle className="text-red-500" />
            Elevated-Risk Merchants ({formatNumber(filteredMerchants.length)})
          </h3>
          <div className="text-xs text-slate-500">
            <span className="text-red-400 font-semibold">{critMerchants}</span> CRITICAL ·{' '}
            <span className="text-orange-400 font-semibold">{highMerchants}</span> HIGH
            {' '}· retrospective risk score (M6)
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
              <tr>
                <th className="p-3">Merchant ID</th>
                <th className="p-3">Category</th>
                <th className="p-3">Risk Level</th>
                <th className="p-3">Retro Score</th>
                <th className="p-3">Txns</th>
                <th className="p-3">Volume</th>
                <th className="p-3">CB Rate</th>
                <th className="p-3">Disputed Ratio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {merchantPageData.map(m => (
                <React.Fragment key={m.merchant_id_normalized}>
                  <tr className="hover:bg-slate-700/30 transition-colors">
                    <td className="p-3 font-mono">{m.merchant_id_normalized}</td>
                    <td className="p-3 text-slate-300">{m.merchant_category_clean}</td>
                    <td className="p-3"><RiskBadge level={m.risk_level} /></td>
                    <td className="p-3 font-bold">{(m.retrospective_risk_score ?? 0).toFixed(1)}</td>
                    <td className="p-3">{formatNumber(m.transaction_count)}</td>
                    <td className="p-3">{formatCurrency(m.total_transaction_amount)}</td>
                    <td className="p-3 text-red-400">{formatPercent(m.chargeback_rate)}</td>
                    <td className="p-3">{formatPercent(m.disputed_amount_ratio)}</td>
                  </tr>
                  <ExplanationRow
                    explanation={m.explanation}
                    signals={[m.top_risk_signal_1, m.top_risk_signal_2, m.top_risk_signal_3]}
                  />
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
          <span>Page {merchantPage + 1} of {merchantPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setMerchantPage(p => Math.max(0, p - 1))}
              disabled={merchantPage === 0}
              className="px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            >← Prev</button>
            <button
              onClick={() => setMerchantPage(p => Math.min(merchantPages - 1, p + 1))}
              disabled={merchantPage === merchantPages - 1}
              className="px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            >Next →</button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default RiskIntelligence;
