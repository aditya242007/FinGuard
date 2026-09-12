import React, { useMemo } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';

import { AlertTriangle, TrendingUp, CheckCircle } from 'lucide-react';



const Overview: React.FC = () => {
  const { data, status, riskLevel, merchantCategory, hasChargeback } = useFilterStore();
  
  const filteredData = useMemo(() => {
    if (!data) return [];
    return data.transactions.filter(t => {
      if (status && t.status_clean !== status) return false;
      if (riskLevel && t.transaction_time_risk_level !== riskLevel) return false;
      if (merchantCategory && t.merchant_category_clean !== merchantCategory) return false;
      if (hasChargeback !== null && Boolean(t.has_chargeback) !== hasChargeback) return false;
      return true;
    });
  }, [data, status, riskLevel, merchantCategory, hasChargeback]);

  if (!data) return null;

  // KPI Calculations
  const totalTxns = filteredData.length;
  const totalValue = filteredData.reduce((sum, t) => sum + (t.amount_abs || 0), 0);
  const avgValue = totalTxns > 0 ? totalValue / totalTxns : 0;
  
  const successCount = filteredData.filter(t => t.status_clean === 'SUCCESS').length;
  const successRate = totalTxns > 0 ? successCount / totalTxns : 0;
  
  const chargebackTxns = filteredData.filter(t => t.has_chargeback).length;
  const chargebackRate = totalTxns > 0 ? chargebackTxns / totalTxns : 0;
  
  const totalDisputed = filteredData.reduce((sum, t) => sum + (t.total_disputed_amount || 0), 0);
  
  // Data Quality Metrics
  const missingKycCount = filteredData.filter(t => t.kyc_status_clean === 'UNKNOWN' || !t.kyc_status_clean).length;
  const missingUtrCount = filteredData.filter(t => t.missing_utr_flag).length;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Executive Overview</h2>
          <p className="text-slate-400">From messy UPI transactions to explainable risk intelligence.</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Total Transactions" value={formatNumber(totalTxns)} icon={<TrendingUp />} />
        <KpiCard title="Total Value" value={formatCurrency(totalValue)} icon={<TrendingUp />} />
        <KpiCard title="Success Rate" value={formatPercent(successRate)} icon={<CheckCircle className="text-green-500" />} />
        <KpiCard title="Chargeback Rate" value={formatPercent(chargebackRate)} icon={<AlertTriangle className="text-red-500" />} />
        <KpiCard title="Disputed Amount" value={formatCurrency(totalDisputed)} />
        <KpiCard title="Average Value" value={formatCurrency(avgValue)} />
        <KpiCard title="Suspicious Clusters" value={formatNumber(data.clusters.length)} />
        <KpiCard title="High/Critical Entities" value={
          formatNumber(data.merchants.filter(m => m.risk_level === 'HIGH' || m.risk_level === 'CRITICAL').length + 
                       data.users.filter(u => u.risk_level === 'HIGH' || u.risk_level === 'CRITICAL').length)
        } />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Data Quality Panel */}
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700 col-span-1 lg:col-span-3">
          <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
            <AlertTriangle size={18} className="text-yellow-500" /> Data Quality Snapshot
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900 p-3 rounded border border-slate-800">
              <p className="text-sm text-slate-400">Missing KYC</p>
              <p className="text-xl font-bold">{formatPercent(missingKycCount / (totalTxns || 1))}</p>
              <p className="text-xs text-slate-500 mt-1">Limits KYC-based interpretation coverage</p>
            </div>
            <div className="bg-slate-900 p-3 rounded border border-slate-800">
              <p className="text-sm text-slate-400">Missing UTR</p>
              <p className="text-xl font-bold">{formatPercent(missingUtrCount / (totalTxns || 1))}</p>
              <p className="text-xs text-slate-500 mt-1">Traceability issue</p>
            </div>
            <div className="bg-slate-900 p-3 rounded border border-slate-800">
              <p className="text-sm text-slate-400">Negative Amounts</p>
              <p className="text-xl font-bold">{formatNumber(filteredData.filter(t => (t.amount_numeric || 0) < 0).length)}</p>
              <p className="text-xs text-slate-500 mt-1">Behavioral anomaly / reversal</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const KpiCard = ({ title, value, icon }: { title: string, value: string, icon?: React.ReactNode }) => (
  <div className="bg-slate-800 p-5 rounded-lg border border-slate-700 flex flex-col justify-between">
    <div className="flex justify-between items-start mb-2">
      <h3 className="text-slate-400 font-medium text-sm">{title}</h3>
      {icon && <div className="text-slate-500">{icon}</div>}
    </div>
    <div className="text-2xl font-bold text-white">{value}</div>
  </div>
);

export default Overview;
