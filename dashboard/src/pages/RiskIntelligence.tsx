import React from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

const RiskIntelligence: React.FC = () => {
  const { data } = useFilterStore();
  
  if (!data) return null;

  const topMerchants = [...data.merchants]
    .sort((a, b) => (b.retrospective_risk_score || 0) - (a.retrospective_risk_score || 0))
    .slice(0, 10);

  const topClusters = [...data.clusters]
    .sort((a, b) => b.cluster_risk_score - a.cluster_risk_score)
    .slice(0, 10);

  const riskBadgeColor = (level?: string) => {
    switch (level) {
      case 'CRITICAL': return 'bg-red-900 text-red-200 border-red-700';
      case 'HIGH': return 'bg-orange-900 text-orange-200 border-orange-700';
      case 'MEDIUM': return 'bg-yellow-900 text-yellow-200 border-yellow-700';
      case 'LOW': return 'bg-green-900 text-green-200 border-green-700';
      default: return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Fraud & Risk Intelligence</h2>
        <p className="text-slate-400">Identify where investigation attention should go.</p>
      </div>

      {/* Investigation Candidates (Clusters) */}
      <section>
        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <ShieldAlert className="text-orange-500" /> Investigation Candidates (Suspicious Clusters)
        </h3>
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400 border-b border-slate-700">
              <tr>
                <th className="p-4">Cluster ID</th>
                <th className="p-4">Risk Level</th>
                <th className="p-4">Score</th>
                <th className="p-4">Entities (U/M)</th>
                <th className="p-4">Txns</th>
                <th className="p-4">CB Rate</th>
                <th className="p-4">Disputed Amt</th>
                <th className="p-4 w-full">Top Signals</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {topClusters.map(c => (
                <tr key={c.cluster_id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="p-4 font-mono font-medium">{c.cluster_id}</td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs border ${riskBadgeColor(c.risk_level)}`}>
                      {c.risk_level}
                    </span>
                  </td>
                  <td className="p-4 font-bold">{c.cluster_risk_score.toFixed(1)}</td>
                  <td className="p-4">{c.n_users} / {c.n_merchants}</td>
                  <td className="p-4">{c.n_transactions}</td>
                  <td className="p-4">{formatPercent(c.cluster_chargeback_rate)}</td>
                  <td className="p-4">{formatCurrency(c.disputed_amount)}</td>
                  <td className="p-4 text-xs text-slate-400 whitespace-normal min-w-[300px]">
                    {c.top_signals.split('|').join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Top Risk Merchants */}
      <section>
        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="text-red-500" /> Top Risk Merchants
        </h3>
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400 border-b border-slate-700">
              <tr>
                <th className="p-4">Merchant ID</th>
                <th className="p-4">Category</th>
                <th className="p-4">Risk Level</th>
                <th className="p-4">Score</th>
                <th className="p-4">Txns</th>
                <th className="p-4">Txn Value</th>
                <th className="p-4">CB Rate</th>
                <th className="p-4">Disputed Amt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {topMerchants.map(m => (
                <tr key={m.merchant_id_normalized} className="hover:bg-slate-700/30 transition-colors">
                  <td className="p-4 font-mono">{m.merchant_id_normalized}</td>
                  <td className="p-4">{m.merchant_category_clean}</td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs border ${riskBadgeColor(m.risk_level)}`}>
                      {m.risk_level || 'UNKNOWN'}
                    </span>
                  </td>
                  <td className="p-4 font-bold">{(m.retrospective_risk_score || 0).toFixed(1)}</td>
                  <td className="p-4">{formatNumber(m.transaction_count)}</td>
                  <td className="p-4">{formatCurrency(m.total_transaction_amount)}</td>
                  <td className="p-4">{formatPercent(m.chargeback_rate)}</td>
                  <td className="p-4">{formatCurrency((m.disputed_amount_ratio || 0) * m.total_transaction_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default RiskIntelligence;
