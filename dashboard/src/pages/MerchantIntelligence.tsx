import React from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency } from '../utils/format';
import { Store, TrendingDown } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const MerchantIntelligence: React.FC = () => {
  const { data, merchantCategory } = useFilterStore();
  
  if (!data) return null;

  let merchants = data.merchants;
  if (merchantCategory) {
    merchants = merchants.filter(m => m.merchant_category_clean === merchantCategory);
  }

  // Aggregate by category
  const categoryAgg = merchants.reduce((acc, m) => {
    const cat = m.merchant_category_clean || 'UNKNOWN';
    if (!acc[cat]) {
      acc[cat] = { category: cat, totalTxns: 0, totalAmount: 0, cbTxns: 0 };
    }
    acc[cat].totalTxns += m.transaction_count;
    acc[cat].totalAmount += m.total_transaction_amount;
    acc[cat].cbTxns += (m.chargeback_rate * m.transaction_count);
    return acc;
  }, {} as Record<string, {category: string, totalTxns: number, totalAmount: number, cbTxns: number}>);

  const chartData = Object.values(categoryAgg)
    .map(c => ({
      ...c,
      cbRate: c.totalTxns > 0 ? (c.cbTxns / c.totalTxns) * 100 : 0
    }))
    .sort((a, b) => b.totalAmount - a.totalAmount)
    .slice(0, 15);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Store className="text-blue-500" /> Merchant Intelligence
        </h2>
        <p className="text-slate-400">Analyze merchant-level volume and risk performance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700 h-80">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Total Value by Category</h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
              <XAxis type="number" stroke="#94a3b8" fontSize={12} tickFormatter={(val) => `₹${val/1000}k`} />
              <YAxis type="category" dataKey="category" stroke="#94a3b8" fontSize={12} width={100} />
              <Tooltip 
                cursor={{fill: '#334155'}}
                contentStyle={{backgroundColor: '#0f172a', borderColor: '#334155'}}
                formatter={(val: any) => formatCurrency(val as number)}
              />
              <Bar dataKey="totalAmount" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700 h-80">
          <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <TrendingDown className="text-red-400" size={16} /> Chargeback Rate by Category (%)
          </h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData.sort((a, b) => b.cbRate - a.cbRate)} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
              <XAxis type="number" stroke="#94a3b8" fontSize={12} />
              <YAxis type="category" dataKey="category" stroke="#94a3b8" fontSize={12} width={100} />
              <Tooltip 
                cursor={{fill: '#334155'}}
                contentStyle={{backgroundColor: '#0f172a', borderColor: '#334155'}}
                formatter={(val: any) => `${Number(val).toFixed(2)}%`}
              />
              <Bar dataKey="cbRate" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Table omitted for brevity in stub */}
    </div>
  );
};

export default MerchantIntelligence;
