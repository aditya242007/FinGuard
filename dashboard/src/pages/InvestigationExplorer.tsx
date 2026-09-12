import React, { useState } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatPercent } from '../utils/format';
import { Search, ShieldAlert, Activity } from 'lucide-react';

const InvestigationExplorer: React.FC = () => {
  const { data } = useFilterStore();
  const [searchTerm, setSearchTerm] = useState('');
  
  if (!data) return null;

  // Extremely naive search for demonstration
  const searchResultCluster = data.clusters.find(c => c.cluster_id.includes(searchTerm));
  const searchResultTxn = data.transactions.find(t => t.txn_id_normalized.includes(searchTerm));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Search className="text-blue-500" /> Investigation Explorer
        </h2>
        <p className="text-slate-400">Search by Cluster ID, Transaction ID, Merchant ID, or User ID.</p>
      </div>

      <div className="max-w-2xl">
        <div className="relative">
          <Search className="absolute left-3 top-3 text-slate-500" size={18} />
          <input 
            type="text" 
            placeholder="Search e.g. CLU00604 or TXN00006755..."
            className="w-full bg-slate-800 border border-slate-700 rounded-md py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {searchTerm && searchResultCluster && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <ShieldAlert className="text-orange-500" /> Cluster Investigation: {searchResultCluster.cluster_id}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Risk Level</p>
              <p className="font-bold text-orange-400">{searchResultCluster.risk_level}</p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Risk Score</p>
              <p className="font-bold text-white">{searchResultCluster.cluster_risk_score.toFixed(1)}</p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Chargeback Rate</p>
              <p className="font-bold text-red-400">{formatPercent(searchResultCluster.cluster_chargeback_rate)}</p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Disputed Amount</p>
              <p className="font-bold text-white">{formatCurrency(searchResultCluster.disputed_amount)}</p>
            </div>
          </div>
          <div className="bg-slate-900/50 p-4 rounded border border-slate-700">
            <h4 className="font-medium text-sm text-slate-300 mb-2">Why is this flagged?</h4>
            <p className="text-sm text-slate-400">{searchResultCluster.explanation}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {searchResultCluster.top_signals.split('|').map(s => (
                <span key={s} className="px-2 py-1 bg-slate-800 border border-slate-600 rounded text-xs text-slate-300">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {searchTerm && searchResultTxn && !searchResultCluster && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <Activity className="text-blue-500" /> Transaction Detail: {searchResultTxn.txn_id_normalized}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Amount</p>
              <p className="font-bold text-white">{formatCurrency(searchResultTxn.amount_abs || 0)}</p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Status</p>
              <p className={`font-bold ${searchResultTxn.status_clean === 'SUCCESS' ? 'text-green-400' : 'text-red-400'}`}>
                {searchResultTxn.status_clean}
              </p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Has Chargeback</p>
              <p className="font-bold text-white">{searchResultTxn.has_chargeback ? 'Yes' : 'No'}</p>
            </div>
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-400">Missing UTR</p>
              <p className="font-bold text-white">{searchResultTxn.missing_utr_flag ? 'Yes' : 'No'}</p>
            </div>
          </div>
        </div>
      )}

      {searchTerm && !searchResultCluster && !searchResultTxn && (
        <p className="text-slate-500">No matching investigation entity found.</p>
      )}
    </div>
  );
};

export default InvestigationExplorer;
