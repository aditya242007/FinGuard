/**
 * FilterBar.tsx
 * =============
 * Global filter bar implementing all 8 required filter dimensions.
 * Filters are non-cosmetic: they feed into useFilterStore which computes
 * filteredTransactions used by every page.
 */
import React, { useMemo, useState } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { Filter, X, ChevronDown } from 'lucide-react';

// ---------------------------------------------------------------------------
// Styled select helper
// ---------------------------------------------------------------------------
const SelectFilter: React.FC<{
  value: string;
  onChange: (v: string) => void;
  label: string;
  children: React.ReactNode;
}> = ({ value, onChange, label, children }) => (
  <div className="relative">
    <label className="block text-xs text-slate-500 mb-1">{label}</label>
    <div className="relative">
      <select
        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200 appearance-none pr-8"
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {children}
      </select>
      <ChevronDown size={14} className="absolute right-2 top-2 text-slate-500 pointer-events-none" />
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// FilterBar
// ---------------------------------------------------------------------------
export const FilterBar: React.FC = () => {
  const {
    data,
    dateStart, dateEnd,
    status, merchantCategory, merchantId, userId,
    riskLevel, hasChargeback, kycStatus,
    filteredTransactions,
    setFilter, resetFilters,
  } = useFilterStore();

  const [expanded, setExpanded] = useState(false);

  const activeCount = [
    dateStart, dateEnd, status, merchantCategory,
    merchantId, userId, riskLevel,
    hasChargeback !== null ? hasChargeback : null,
    kycStatus,
  ].filter(v => v !== null && v !== undefined).length;

  const derived = useMemo(() => {
    if (!data) return { categories: [], statuses: [], kycStatuses: [] };
    const txns = data.transactions;
    return {
      categories: Array.from(new Set(txns.map(t => t.merchant_category_clean).filter(Boolean))).sort(),
      statuses: Array.from(new Set(txns.map(t => t.status_clean).filter(Boolean))).sort(),
      kycStatuses: Array.from(new Set(txns.map(t => t.kyc_status_clean).filter(Boolean))).sort(),
    };
  }, [data]);

  if (!data) return null;

  return (
    <div className="bg-slate-900 border-b border-slate-800 sticky top-0 z-20">
      {/* Primary row */}
      <div className="flex items-center gap-3 px-6 py-3 flex-wrap">
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
        >
          <Filter size={15} />
          <span>Global Filters</span>
          {activeCount > 0 && (
            <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
              {activeCount}
            </span>
          )}
          <ChevronDown
            size={14}
            className={`text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
          />
        </button>

        {/* Quick stats from filtered set */}
        <div className="ml-auto flex items-center gap-4 text-xs text-slate-500">
          <span>
            <span className="text-slate-300 font-medium">{filteredTransactions.length.toLocaleString('en-IN')}</span> transactions
          </span>
          <span>
            <span className="text-slate-300 font-medium">
              {filteredTransactions.filter(t => t.has_chargeback).length.toLocaleString('en-IN')}
            </span> with chargebacks
          </span>
          {activeCount > 0 && (
            <button
              onClick={resetFilters}
              className="flex items-center gap-1 text-red-400 hover:text-red-200 transition-colors"
            >
              <X size={13} /> Reset all
            </button>
          )}
        </div>
      </div>

      {/* Expanded filter panel */}
      {expanded && (
        <div className="border-t border-slate-800 px-6 py-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">

          {/* 1. Date Start */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">From Date</label>
            <input
              type="date"
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
              value={dateStart ?? ''}
              onChange={e => setFilter('dateStart', e.target.value || null)}
            />
          </div>

          {/* 2. Date End */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">To Date</label>
            <input
              type="date"
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
              value={dateEnd ?? ''}
              onChange={e => setFilter('dateEnd', e.target.value || null)}
            />
          </div>

          {/* 3. Status */}
          <SelectFilter
            label="Status"
            value={status ?? ''}
            onChange={v => setFilter('status', v || null)}
          >
            <option value="">All Statuses</option>
            {derived.statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </SelectFilter>

          {/* 4. Merchant Category */}
          <SelectFilter
            label="Merchant Category"
            value={merchantCategory ?? ''}
            onChange={v => setFilter('merchantCategory', v || null)}
          >
            <option value="">All Categories</option>
            {derived.categories.map(c => <option key={c} value={c}>{c}</option>)}
          </SelectFilter>

          {/* 5. Risk Level (transaction-time, from M6) */}
          <SelectFilter
            label="Risk Level (Txn-Time)"
            value={riskLevel ?? ''}
            onChange={v => setFilter('riskLevel', v || null)}
          >
            <option value="">All Risk Levels</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </SelectFilter>

          {/* 6. Chargeback Presence */}
          <SelectFilter
            label="Chargeback"
            value={hasChargeback === null ? '' : String(hasChargeback)}
            onChange={v => setFilter('hasChargeback', v === '' ? null : v === 'true')}
          >
            <option value="">All</option>
            <option value="true">Has Chargeback</option>
            <option value="false">No Chargeback</option>
          </SelectFilter>

          {/* 7. KYC Status */}
          <SelectFilter
            label="KYC Status"
            value={kycStatus ?? ''}
            onChange={v => setFilter('kycStatus', v || null)}
          >
            <option value="">All KYC</option>
            {derived.kycStatuses.map(k => <option key={k} value={k}>{k}</option>)}
          </SelectFilter>

          {/* 8. User ID (free text) */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">User ID</label>
            <input
              type="text"
              placeholder="e.g. USR40970"
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
              value={userId ?? ''}
              onChange={e => setFilter('userId', e.target.value || null)}
            />
          </div>

          {/* 9. Merchant ID (free text — listed as one of 8 required) */}
          <div className="sm:col-span-2 lg:col-span-1">
            <label className="block text-xs text-slate-500 mb-1">Merchant ID</label>
            <input
              type="text"
              placeholder="e.g. MCH6502"
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 text-slate-200"
              value={merchantId ?? ''}
              onChange={e => setFilter('merchantId', e.target.value || null)}
            />
          </div>
        </div>
      )}
    </div>
  );
};
