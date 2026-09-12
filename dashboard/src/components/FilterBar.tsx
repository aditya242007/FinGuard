import React from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { Filter, X } from 'lucide-react';

export const FilterBar: React.FC = () => {
  const {
    status, merchantCategory, riskLevel, hasChargeback,
    setFilter, resetFilters, data
  } = useFilterStore();

  const activeFiltersCount = [status, merchantCategory, riskLevel, hasChargeback].filter(Boolean).length;

  if (!data) return null;

  // Extract unique values for filters
  const categories = Array.from(new Set(data.transactions.map(t => t.merchant_category_clean).filter(Boolean)));
  const statuses = Array.from(new Set(data.transactions.map(t => t.status_clean).filter(Boolean)));

  return (
    <div className="bg-slate-800 border-b border-slate-700 p-4 sticky top-0 z-10 flex flex-wrap gap-4 items-center">
      <div className="flex items-center gap-2 text-slate-300 font-medium mr-4">
        <Filter size={18} />
        <span>Global Filters</span>
        {activeFiltersCount > 0 && (
          <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
            {activeFiltersCount}
          </span>
        )}
      </div>

      <select 
        className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
        value={riskLevel || ''}
        onChange={(e) => setFilter('riskLevel', e.target.value || null)}
      >
        <option value="">All Risk Levels</option>
        <option value="LOW">Low Risk</option>
        <option value="MEDIUM">Medium Risk</option>
        <option value="HIGH">High Risk</option>
        <option value="CRITICAL">Critical Risk</option>
      </select>

      <select 
        className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
        value={status || ''}
        onChange={(e) => setFilter('status', e.target.value || null)}
      >
        <option value="">All Statuses</option>
        {statuses.map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      <select 
        className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200 max-w-[200px]"
        value={merchantCategory || ''}
        onChange={(e) => setFilter('merchantCategory', e.target.value || null)}
      >
        <option value="">All Categories</option>
        {categories.map(c => <option key={c} value={c}>{c}</option>)}
      </select>

      <select 
        className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
        value={hasChargeback === null ? '' : hasChargeback.toString()}
        onChange={(e) => {
          const val = e.target.value;
          setFilter('hasChargeback', val === '' ? null : val === 'true');
        }}
      >
        <option value="">All Chargeback Status</option>
        <option value="true">Has Chargeback</option>
        <option value="false">No Chargeback</option>
      </select>

      {activeFiltersCount > 0 && (
        <button 
          onClick={resetFilters}
          className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition-colors ml-auto"
        >
          <X size={14} /> Reset
        </button>
      )}
    </div>
  );
};
