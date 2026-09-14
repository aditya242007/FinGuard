/**
 * MerchantIntelligence.tsx — Merchant Intelligence
 * Merchant KPIs and charts respond to all global filters.
 * Aggregates are computed from filtered transaction records, not pre-baked.
 */
import React, { useMemo, useState } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';
import { Store, TrendingDown, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

// ---------------------------------------------------------------------------
// Risk badge
// ---------------------------------------------------------------------------
const RiskBadge: React.FC<{ level?: string }> = ({ level }) => {
  const cls =
    level === 'CRITICAL' ? 'bg-red-900/60 text-red-300 border-red-700' :
    level === 'HIGH'     ? 'bg-orange-900/60 text-orange-300 border-orange-700' :
    level === 'MEDIUM'   ? 'bg-yellow-900/60 text-yellow-300 border-yellow-700' :
    level === 'LOW'      ? 'bg-green-900/60 text-green-300 border-green-700' :
    'bg-slate-800 text-slate-400 border-slate-700';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${cls}`}>
      {level ?? 'UNKNOWN'}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
const ChartTooltip: React.FC<{ active?: boolean; payload?: any[]; label?: string; isCurrency?: boolean }> = ({
  active, payload, label, isCurrency
}) => {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value ?? 0;
  return (
    <div className="bg-slate-900 border border-slate-700 rounded p-3 text-xs shadow-lg">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      <p className="text-white font-bold">
        {isCurrency ? formatCurrency(val) : `${Number(val).toFixed(2)}%`}
      </p>
    </div>
  );
};

const PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// MerchantIntelligence
// ---------------------------------------------------------------------------
const MerchantIntelligence: React.FC = () => {
  const { data, filteredTransactions, merchantCategory, riskLevel } = useFilterStore();
  const [tablePage, setTablePage] = useState(0);

  if (!data) return null;

  // ── Scope merchants to those present in filtered transactions ──────────
  const filteredMerchantIds = useMemo(() =>
    new Set(filteredTransactions.map(t => t.merchant_id_normalized)),
    [filteredTransactions]
  );

  // Apply category + riskLevel from store to merchant list
  const filteredMerchants = useMemo(() => {
    return data.merchants.filter(m => {
      if (!filteredMerchantIds.has(m.merchant_id_normalized)) return false;
      if (merchantCategory && m.merchant_category_clean !== merchantCategory) return false;
      if (riskLevel && m.risk_level !== riskLevel) return false;
      return true;
    });
  }, [data.merchants, filteredMerchantIds, merchantCategory, riskLevel]);

  // ── Category aggregates from filtered transactions ─────────────────────
  const categoryStats = useMemo(() => {
    const agg: Record<string, { totalAmount: number; totalTxns: number; cbTxns: number }> = {};
    for (const t of filteredTransactions) {
      const cat = t.merchant_category_clean || 'UNKNOWN';
      if (!agg[cat]) agg[cat] = { totalAmount: 0, totalTxns: 0, cbTxns: 0 };
      agg[cat].totalAmount += t.amount_numeric;
      agg[cat].totalTxns += 1;
      if (t.has_chargeback) agg[cat].cbTxns += 1;
    }
    return Object.entries(agg)
      .map(([category, d]) => ({
        category,
        totalAmount: d.totalAmount,
        totalTxns: d.totalTxns,
        cbRate: d.totalTxns > 0 ? (d.cbTxns / d.totalTxns) * 100 : 0,
      }))
      .sort((a, b) => b.totalAmount - a.totalAmount);
  }, [filteredTransactions]);

  // Top 15 for volume chart, sorted by cbRate for cb chart
  const volumeChartData = categoryStats.slice(0, 15);
  const cbRateChartData = [...categoryStats].sort((a, b) => b.cbRate - a.cbRate).slice(0, 15);

  // Sorted merchant table
  const sortedMerchants = [...filteredMerchants].sort((a, b) =>
    (b.retrospective_risk_score ?? 0) - (a.retrospective_risk_score ?? 0)
  );
  const tableData = sortedMerchants.slice(tablePage * PAGE_SIZE, (tablePage + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(sortedMerchants.length / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Store className="text-blue-500" /> Merchant Intelligence
        </h2>
        <p className="text-slate-400">
          Merchant volume and risk performance — scoped to current global filters.
          Amounts use authoritative amount_numeric (signed, M2).
        </p>
      </div>

      {/* ── Summary stats ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <p className="text-xs text-slate-500">Active Merchants (filtered)</p>
          <p className="text-2xl font-bold text-white">{formatNumber(filteredMerchants.length)}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <p className="text-xs text-slate-500">Categories</p>
          <p className="text-2xl font-bold text-white">{categoryStats.length}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <p className="text-xs text-slate-500">Total Volume (filtered txns)</p>
          <p className="text-2xl font-bold text-white">
            {formatCurrency(filteredTransactions.reduce((s, t) => s + t.amount_numeric, 0))}
          </p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <p className="text-xs text-slate-500">HIGH/CRITICAL Merchants</p>
          <p className="text-2xl font-bold text-orange-400">
            {filteredMerchants.filter(m => m.risk_level === 'HIGH' || m.risk_level === 'CRITICAL').length}
          </p>
        </div>
      </div>

      {/* ── Charts ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volume by category */}
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Transaction Volume by Category (top 15, signed amount_numeric)
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={volumeChartData} layout="vertical" margin={{ top: 0, right: 16, left: 80, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#475569" fontSize={11}
                tickFormatter={v => `₹${(v / 1_000_000).toFixed(1)}M`} />
              <YAxis type="category" dataKey="category" stroke="#475569" fontSize={11} width={80} />
              <Tooltip content={<ChartTooltip isCurrency />} />
              <Bar dataKey="totalAmount" radius={[0, 3, 3, 0]}>
                {volumeChartData.map((_, i) => (
                  <Cell key={i} fill={`hsl(${210 + i * 8}, 70%, 55%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* CB rate by category */}
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <TrendingDown className="text-red-400" size={15} />
            Chargeback Rate by Category (%, top 15 by rate)
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={cbRateChartData} layout="vertical" margin={{ top: 0, right: 16, left: 80, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#475569" fontSize={11} tickFormatter={v => `${v.toFixed(1)}%`} />
              <YAxis type="category" dataKey="category" stroke="#475569" fontSize={11} width={80} />
              <Tooltip content={<ChartTooltip isCurrency={false} />} />
              <Bar dataKey="cbRate" radius={[0, 3, 3, 0]}>
                {cbRateChartData.map((_, i) => (
                  <Cell key={i} fill={`hsl(${0 + i * 5}, 70%, 50%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Merchant table ───────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">
            Merchant List ({formatNumber(sortedMerchants.length)})
          </h3>
          <p className="text-xs text-slate-500">Sorted by retrospective risk score (M6)</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
              <tr>
                <th className="p-3">Merchant ID</th>
                <th className="p-3">Category</th>
                <th className="p-3">Status</th>
                <th className="p-3">Risk Level</th>
                <th className="p-3">Retro Score</th>
                <th className="p-3">Txns</th>
                <th className="p-3">Volume</th>
                <th className="p-3">CB Rate</th>
                <th className="p-3">Disputed Ratio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {tableData.map(m => (
                <tr key={m.merchant_id_normalized} className="hover:bg-slate-700/30 transition-colors">
                  <td className="p-3 font-mono text-slate-200">{m.merchant_id_normalized}</td>
                  <td className="p-3 text-slate-300">{m.merchant_category_clean}</td>
                  <td className="p-3 text-slate-400">{m.merchant_status_clean}</td>
                  <td className="p-3"><RiskBadge level={m.risk_level} /></td>
                  <td className="p-3 font-bold">{(m.retrospective_risk_score ?? 0).toFixed(1)}</td>
                  <td className="p-3">{formatNumber(m.transaction_count)}</td>
                  <td className="p-3">{formatCurrency(m.total_transaction_amount)}</td>
                  <td className="p-3 text-red-400">{formatPercent(m.chargeback_rate)}</td>
                  <td className="p-3">{formatPercent(m.disputed_amount_ratio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
          <span>
            Showing {tablePage * PAGE_SIZE + 1}–{Math.min((tablePage + 1) * PAGE_SIZE, sortedMerchants.length)} of {formatNumber(sortedMerchants.length)}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setTablePage(p => Math.max(0, p - 1))}
              disabled={tablePage === 0}
              className="flex items-center gap-1 px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            ><ChevronLeft size={13} /> Prev</button>
            <button
              onClick={() => setTablePage(p => Math.min(totalPages - 1, p + 1))}
              disabled={tablePage >= totalPages - 1}
              className="flex items-center gap-1 px-3 py-1 bg-slate-800 border border-slate-700 rounded disabled:opacity-40 hover:bg-slate-700 transition-colors"
            >Next <ChevronRight size={13} /></button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MerchantIntelligence;
