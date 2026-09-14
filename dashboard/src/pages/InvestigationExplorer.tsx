/**
 * InvestigationExplorer.tsx — Entity Investigation
 * =================================================
 * Genuine entity-based investigation. Evidence comes entirely from
 * M3–M7 processed outputs (no fabricated relationships).
 *
 * Supported search entities:
 *   CLUxxxxx → cluster → users → transactions → merchants → chargebacks
 *   TXNxxxxx → transaction detail with M6 risk signals
 *   USRxxxxx → user detail → their transactions → chargebacks
 *   MCHxxxxx → merchant detail → their transactions → chargebacks
 *
 * Risk signals use M6 terminology only.
 */
import React, { useMemo, useState } from 'react';
import { useFilterStore } from '../store/useFilterStore';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format';
import { Search, ShieldAlert, Activity, Users, Store, AlertTriangle, Clock, Info } from 'lucide-react';
import type { Transaction, ChargebackRecord, SuspiciousCluster, UserAnalytics, MerchantAnalytics } from '../utils/dataLoader';

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
// Signal tag
// ---------------------------------------------------------------------------
const Signal: React.FC<{ label: string }> = ({ label }) =>
  label ? (
    <span className="px-2 py-0.5 bg-slate-800 border border-slate-600 rounded text-xs text-slate-300">
      {label}
    </span>
  ) : null;

// ---------------------------------------------------------------------------
// Section card wrapper
// ---------------------------------------------------------------------------
const SectionCard: React.FC<{ title: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  title, children, className = ''
}) => (
  <div className={`bg-slate-800 border border-slate-700 rounded-lg overflow-hidden ${className}`}>
    <div className="px-5 py-3 border-b border-slate-700 bg-slate-900/40">
      <h4 className="font-semibold text-sm text-slate-200 flex items-center gap-2">{title}</h4>
    </div>
    <div className="p-5">{children}</div>
  </div>
);

// ---------------------------------------------------------------------------
// Transaction mini-row
// ---------------------------------------------------------------------------
const TxnRow: React.FC<{ txn: Transaction; chargeback?: ChargebackRecord }> = ({ txn, chargeback }) => (
  <div className="py-3 border-b border-slate-700/50 last:border-0">
    <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
      <span className="font-mono text-slate-200">{txn.txn_id_normalized}</span>
      <span className="text-slate-400">{txn.timestamp_clean?.slice(0, 10)}</span>
      <span className={`font-medium ${txn.status_clean === 'SUCCESS' ? 'text-green-400' : txn.status_clean === 'FAILED' ? 'text-red-400' : 'text-yellow-400'}`}>
        {txn.status_clean}
      </span>
      <span className="text-white font-semibold">{formatCurrency(txn.amount_numeric)}</span>
      {txn.has_chargeback && (
        <span className="flex items-center gap-1 text-red-400 text-xs">
          <AlertTriangle size={11} /> Chargeback
        </span>
      )}
    </div>
    <div className="mt-1 flex flex-wrap gap-2">
      <span className="text-xs text-slate-500">Txn-time risk:</span>
      <RiskBadge level={txn.transaction_time_risk_level} />
      <span className="text-xs text-slate-500 ml-2">Retrospective:</span>
      <RiskBadge level={txn.retrospective_risk_level} />
    </div>
    {txn.explanation && (
      <p className="text-xs text-slate-500 mt-1 italic">{txn.explanation}</p>
    )}
    {/* Flags */}
    <div className="mt-1 flex flex-wrap gap-2">
      {txn.utr_missing_flag && <span className="text-xs text-yellow-500">⚠ Missing UTR</span>}
      {txn.amount_negative_flag && <span className="text-xs text-orange-400">⚠ Negative Amount</span>}
      {!txn.transaction_has_kyc && <span className="text-xs text-red-400">⚠ No KYC Match</span>}
      {!txn.transaction_has_merchant && <span className="text-xs text-red-400">⚠ No Merchant Match</span>}
    </div>
    {/* Chargeback detail */}
    {chargeback && (
      <div className="mt-2 bg-red-950/30 border border-red-900/50 rounded p-2 text-xs">
        <span className="text-red-400 font-semibold flex items-center gap-1">
          <Clock size={11} /> Chargeback Records: {chargeback.chargeback_count}
        </span>
        <div className="mt-1 text-slate-400 grid grid-cols-2 gap-x-4">
          <span>Disputed: {formatCurrency(chargeback.total_disputed_amount)}</span>
          <span>Severity: {chargeback.max_severity}</span>
          <span>First filed: {chargeback.first_chargeback_timestamp?.slice(0, 10)}</span>
          <span>Latest filed: {chargeback.latest_chargeback_timestamp?.slice(0, 10)}</span>
        </div>
      </div>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Cluster Detail
// ---------------------------------------------------------------------------
const ClusterDetail: React.FC<{
  cluster: SuspiciousCluster;
  users: UserAnalytics[];
  merchants: MerchantAnalytics[];
  transactions: Transaction[];
  chargebackMap: Map<string, ChargebackRecord>;
}> = ({ cluster, users, merchants, transactions, chargebackMap }) => {
  const [showTxns, setShowTxns] = useState(false);

  return (
    <div className="space-y-4">
      {/* Header */}
      <SectionCard title={<><ShieldAlert size={16} className="text-orange-400" /> Cluster: {cluster.cluster_id}</>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-xs text-slate-500">Risk Level</p>
            <RiskBadge level={cluster.risk_level} />
          </div>
          <div>
            <p className="text-xs text-slate-500">Risk Score</p>
            <p className="font-bold text-white">{cluster.cluster_risk_score.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Chargeback Rate</p>
            <p className="font-bold text-red-400">{formatPercent(cluster.cluster_chargeback_rate)}</p>
            <p className="text-xs text-slate-600">{cluster.chargebacked_transaction_count} txns with ≥1 CB / {cluster.n_transactions} total</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">CB Records (raw)</p>
            <p className="font-bold text-white">{cluster.chargeback_count}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Disputed Amount</p>
            <p className="font-bold text-white">{formatCurrency(cluster.disputed_amount)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Disputed Ratio</p>
            <p className="font-bold">{formatPercent(cluster.disputed_amount_ratio)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Users / Merchants / Txns</p>
            <p className="font-bold text-white">{cluster.n_users} / {cluster.n_merchants} / {cluster.n_transactions}</p>
          </div>
        </div>

        {/* Signals */}
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">Behavioral Risk Signals</p>
          <div className="flex flex-wrap gap-2">
            {cluster.top_signals.split('|').filter(Boolean).map(s => (
              <Signal key={s} label={s} />
            ))}
          </div>
        </div>

        {/* Explanation */}
        {cluster.explanation && (
          <div className="bg-slate-900/50 border border-slate-700 rounded p-3">
            <p className="text-xs text-slate-500 flex items-center gap-1 mb-1">
              <Info size={11} /> Why flagged
            </p>
            <p className="text-xs text-slate-300">{cluster.explanation}</p>
          </div>
        )}
      </SectionCard>

      {/* Members: Users */}
      <SectionCard title={<><Users size={14} className="text-blue-400" /> Cluster Users ({users.length})</>}>
        {users.length === 0
          ? <p className="text-xs text-slate-500">No users in cluster member list.</p>
          : (
            <div className="divide-y divide-slate-700/50">
              {users.map(u => (
                <div key={u.user_id_normalized} className="py-2.5 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                  <span className="font-mono text-slate-200">{u.user_id_normalized}</span>
                  <span className="text-slate-400">KYC: {u.kyc_status_clean}</span>
                  <span className="text-slate-400">Txns: {u.transaction_count}</span>
                  <span className="text-slate-400">Volume: {formatCurrency(u.total_transaction_amount)}</span>
                  <span className="text-red-400">CB: {u.chargeback_count}</span>
                  <RiskBadge level={u.risk_level} />
                </div>
              ))}
            </div>
          )
        }
      </SectionCard>

      {/* Members: Merchants */}
      <SectionCard title={<><Store size={14} className="text-blue-400" /> Cluster Merchants ({merchants.length})</>}>
        {merchants.length === 0
          ? <p className="text-xs text-slate-500">No merchants in cluster member list.</p>
          : (
            <div className="divide-y divide-slate-700/50">
              {merchants.map(m => (
                <div key={m.merchant_id_normalized} className="py-2.5 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                  <span className="font-mono text-slate-200">{m.merchant_id_normalized}</span>
                  <span className="text-slate-400">{m.merchant_category_clean}</span>
                  <span className="text-slate-400">Txns: {m.transaction_count}</span>
                  <span className="text-slate-400">Volume: {formatCurrency(m.total_transaction_amount)}</span>
                  <span className="text-red-400">CB Rate: {formatPercent(m.chargeback_rate)}</span>
                  <RiskBadge level={m.risk_level} />
                </div>
              ))}
            </div>
          )
        }
      </SectionCard>

      {/* Transactions in cluster */}
      <SectionCard title={
        <><Activity size={14} className="text-blue-400" /> Cluster Transactions ({transactions.length})
          <button
            className="ml-3 text-xs text-blue-400 hover:text-blue-200"
            onClick={() => setShowTxns(s => !s)}
          >
            {showTxns ? '▲ Collapse' : '▼ Expand'}
          </button>
        </>
      }>
        {!showTxns
          ? <p className="text-xs text-slate-500">Click "Expand" to view individual transactions.</p>
          : transactions.length === 0
            ? <p className="text-xs text-slate-500">No transactions matched for cluster members.</p>
            : <div className="max-h-96 overflow-y-auto">
                {transactions.map(t => (
                  <TxnRow key={t.txn_id_normalized} txn={t} chargeback={chargebackMap.get(t.txn_id_normalized)} />
                ))}
              </div>
        }
      </SectionCard>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Transaction Detail
// ---------------------------------------------------------------------------
const TransactionDetail: React.FC<{
  txn: Transaction;
  user?: UserAnalytics;
  merchant?: MerchantAnalytics;
  chargeback?: ChargebackRecord;
}> = ({ txn, user, merchant, chargeback }) => (
  <div className="space-y-4">
    <SectionCard title={<><Activity size={16} className="text-blue-400" /> Transaction: {txn.txn_id_normalized}</>}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div><p className="text-xs text-slate-500">Date</p><p className="font-semibold text-white">{txn.timestamp_clean?.slice(0, 10)}</p></div>
        <div>
          <p className="text-xs text-slate-500">Status</p>
          <p className={`font-bold ${txn.status_clean === 'SUCCESS' ? 'text-green-400' : txn.status_clean === 'FAILED' ? 'text-red-400' : 'text-yellow-400'}`}>
            {txn.status_clean}
          </p>
        </div>
        <div><p className="text-xs text-slate-500">Amount (amount_numeric)</p><p className="font-bold text-white">{formatCurrency(txn.amount_numeric)}</p></div>
        <div><p className="text-xs text-slate-500">Category</p><p className="font-semibold text-white">{txn.merchant_category_clean}</p></div>
        <div><p className="text-xs text-slate-500">KYC Status</p><p className="font-semibold text-white">{txn.kyc_status_clean}</p></div>
        <div>
          <p className="text-xs text-slate-500">Txn-Time Risk</p>
          <RiskBadge level={txn.transaction_time_risk_level} />
          <p className="text-xs text-slate-600 mt-0.5">Score: {(txn.transaction_time_risk_score ?? 0).toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Retrospective Risk</p>
          <RiskBadge level={txn.retrospective_risk_level} />
          <p className="text-xs text-slate-600 mt-0.5">Score: {(txn.retrospective_risk_score ?? 0).toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Has Chargeback</p>
          <p className={`font-bold ${txn.has_chargeback ? 'text-red-400' : 'text-green-400'}`}>
            {txn.has_chargeback ? 'Yes' : 'No'}
          </p>
        </div>
      </div>

      {/* Behavioral signals */}
      <div className="mb-3 flex flex-wrap gap-2">
        {[txn.top_risk_signal_1, txn.top_risk_signal_2, txn.top_risk_signal_3].filter(Boolean).map(s => (
          <Signal key={s} label={s} />
        ))}
      </div>
      {txn.explanation && (
        <div className="bg-slate-900/50 border border-slate-700 rounded p-3">
          <p className="text-xs text-slate-500 mb-1"><Info size={11} className="inline mr-1" />Behavioral risk explanation (M6)</p>
          <p className="text-xs text-slate-300">{txn.explanation}</p>
        </div>
      )}

      {/* Data quality flags */}
      <div className="mt-3 flex flex-wrap gap-3">
        {txn.utr_missing_flag && <span className="text-xs text-yellow-400">⚠ Missing UTR</span>}
        {txn.amount_negative_flag && <span className="text-xs text-orange-400">⚠ Negative Amount</span>}
        {!txn.transaction_has_kyc && <span className="text-xs text-red-400">⚠ No KYC record match</span>}
        {!txn.transaction_has_merchant && <span className="text-xs text-red-400">⚠ No merchant record match</span>}
      </div>
    </SectionCard>

    {chargeback && (
      <SectionCard title={<><AlertTriangle size={14} className="text-red-400" /> Chargeback Records</>}>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div><p className="text-xs text-slate-500">Records Count</p><p className="font-bold text-red-400">{chargeback.chargeback_count}</p></div>
          <div><p className="text-xs text-slate-500">Total Disputed</p><p className="font-bold text-white">{formatCurrency(chargeback.total_disputed_amount)}</p></div>
          <div><p className="text-xs text-slate-500">Max Severity</p><p className="font-bold text-white">{chargeback.max_severity}</p></div>
          <div><p className="text-xs text-slate-500">First Filed</p><p className="text-white">{chargeback.first_chargeback_timestamp?.slice(0, 10)}</p></div>
          <div><p className="text-xs text-slate-500">Latest Filed</p><p className="text-white">{chargeback.latest_chargeback_timestamp?.slice(0, 10)}</p></div>
        </div>
      </SectionCard>
    )}

    {user && (
      <SectionCard title={<><Users size={14} className="text-blue-400" /> User: {txn.user_id_normalized}</>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p className="text-xs text-slate-500">Transactions</p><p className="font-bold text-white">{user.transaction_count}</p></div>
          <div><p className="text-xs text-slate-500">Volume</p><p className="font-bold text-white">{formatCurrency(user.total_transaction_amount)}</p></div>
          <div><p className="text-xs text-slate-500">Chargeback Count</p><p className="font-bold text-red-400">{user.chargeback_count}</p></div>
          <div><p className="text-xs text-slate-500">KYC</p><p className="font-bold text-white">{user.kyc_status_clean}</p></div>
          <div><p className="text-xs text-slate-500">Risk Level (Retro)</p><RiskBadge level={user.risk_level} /></div>
          <div><p className="text-xs text-slate-500">Retro Score</p><p className="font-bold text-white">{(user.retrospective_risk_score ?? 0).toFixed(1)}</p></div>
        </div>
        {user.explanation && <p className="mt-3 text-xs text-slate-500">{user.explanation}</p>}
      </SectionCard>
    )}

    {merchant && (
      <SectionCard title={<><Store size={14} className="text-blue-400" /> Merchant: {txn.merchant_id_normalized}</>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p className="text-xs text-slate-500">Category</p><p className="font-bold text-white">{merchant.merchant_category_clean}</p></div>
          <div><p className="text-xs text-slate-500">Transactions</p><p className="font-bold text-white">{merchant.transaction_count}</p></div>
          <div><p className="text-xs text-slate-500">Volume</p><p className="font-bold text-white">{formatCurrency(merchant.total_transaction_amount)}</p></div>
          <div><p className="text-xs text-slate-500">Chargeback Rate</p><p className="font-bold text-red-400">{formatPercent(merchant.chargeback_rate)}</p></div>
          <div><p className="text-xs text-slate-500">Risk Level (Retro)</p><RiskBadge level={merchant.risk_level} /></div>
          <div><p className="text-xs text-slate-500">Retro Score</p><p className="font-bold text-white">{(merchant.retrospective_risk_score ?? 0).toFixed(1)}</p></div>
        </div>
        {merchant.explanation && <p className="mt-3 text-xs text-slate-500">{merchant.explanation}</p>}
      </SectionCard>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// User Detail
// ---------------------------------------------------------------------------
const UserDetail: React.FC<{
  user: UserAnalytics;
  transactions: Transaction[];
  chargebackMap: Map<string, ChargebackRecord>;
}> = ({ user, transactions, chargebackMap }) => {
  const [showTxns, setShowTxns] = useState(false);
  return (
    <div className="space-y-4">
      <SectionCard title={<><Users size={16} className="text-blue-400" /> User: {user.user_id_normalized}</>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
          <div><p className="text-xs text-slate-500">Transactions</p><p className="font-bold text-white">{formatNumber(user.transaction_count)}</p></div>
          <div><p className="text-xs text-slate-500">Volume</p><p className="font-bold text-white">{formatCurrency(user.total_transaction_amount)}</p></div>
          <div><p className="text-xs text-slate-500">Chargeback Count</p><p className="font-bold text-red-400">{user.chargeback_count}</p></div>
          <div><p className="text-xs text-slate-500">Disputed Amount</p><p className="font-bold text-white">{formatCurrency(user.total_disputed_amount)}</p></div>
          <div><p className="text-xs text-slate-500">KYC Status</p><p className="font-bold text-white">{user.kyc_status_clean}</p></div>
          <div><p className="text-xs text-slate-500">Risk Level (Retro)</p><RiskBadge level={user.risk_level} /></div>
          <div><p className="text-xs text-slate-500">Retro Score</p><p className="font-bold text-white">{(user.retrospective_risk_score ?? 0).toFixed(1)}</p></div>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          {[user.top_risk_signal_1, user.top_risk_signal_2, user.top_risk_signal_3].filter(Boolean).map(s => (
            <Signal key={s} label={s} />
          ))}
        </div>
        {user.explanation && (
          <p className="text-xs text-slate-500 italic">{user.explanation}</p>
        )}
      </SectionCard>

      <SectionCard title={
        <><Activity size={14} className="text-blue-400" /> User Transactions ({transactions.length})
          <button className="ml-3 text-xs text-blue-400 hover:text-blue-200" onClick={() => setShowTxns(s => !s)}>
            {showTxns ? '▲ Collapse' : '▼ Expand'}
          </button>
        </>
      }>
        {!showTxns
          ? <p className="text-xs text-slate-500">Click "Expand" to view transactions.</p>
          : <div className="max-h-96 overflow-y-auto">
              {transactions.map(t => (
                <TxnRow key={t.txn_id_normalized} txn={t} chargeback={chargebackMap.get(t.txn_id_normalized)} />
              ))}
            </div>
        }
      </SectionCard>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Merchant Detail
// ---------------------------------------------------------------------------
const MerchantDetail: React.FC<{
  merchant: MerchantAnalytics;
  transactions: Transaction[];
  chargebackMap: Map<string, ChargebackRecord>;
}> = ({ merchant, transactions, chargebackMap }) => {
  const [showTxns, setShowTxns] = useState(false);
  return (
    <div className="space-y-4">
      <SectionCard title={<><Store size={16} className="text-blue-400" /> Merchant: {merchant.merchant_id_normalized}</>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
          <div><p className="text-xs text-slate-500">Category</p><p className="font-bold text-white">{merchant.merchant_category_clean}</p></div>
          <div><p className="text-xs text-slate-500">Status</p><p className="font-bold text-white">{merchant.merchant_status_clean}</p></div>
          <div><p className="text-xs text-slate-500">Transactions</p><p className="font-bold text-white">{formatNumber(merchant.transaction_count)}</p></div>
          <div><p className="text-xs text-slate-500">Volume</p><p className="font-bold text-white">{formatCurrency(merchant.total_transaction_amount)}</p></div>
          <div><p className="text-xs text-slate-500">CB Rate</p><p className="font-bold text-red-400">{formatPercent(merchant.chargeback_rate)}</p></div>
          <div><p className="text-xs text-slate-500">Disputed Ratio</p><p className="font-bold">{formatPercent(merchant.disputed_amount_ratio)}</p></div>
          <div><p className="text-xs text-slate-500">Risk Level (Retro)</p><RiskBadge level={merchant.risk_level} /></div>
          <div><p className="text-xs text-slate-500">Retro Score</p><p className="font-bold text-white">{(merchant.retrospective_risk_score ?? 0).toFixed(1)}</p></div>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          {[merchant.top_risk_signal_1, merchant.top_risk_signal_2, merchant.top_risk_signal_3].filter(Boolean).map(s => (
            <Signal key={s} label={s} />
          ))}
        </div>
        {merchant.explanation && (
          <p className="text-xs text-slate-500 italic">{merchant.explanation}</p>
        )}
      </SectionCard>

      <SectionCard title={
        <><Activity size={14} className="text-blue-400" /> Merchant Transactions ({transactions.length})
          <button className="ml-3 text-xs text-blue-400 hover:text-blue-200" onClick={() => setShowTxns(s => !s)}>
            {showTxns ? '▲ Collapse' : '▼ Expand'}
          </button>
        </>
      }>
        {!showTxns
          ? <p className="text-xs text-slate-500">Click "Expand" to view transactions.</p>
          : <div className="max-h-96 overflow-y-auto">
              {transactions.map(t => (
                <TxnRow key={t.txn_id_normalized} txn={t} chargeback={chargebackMap.get(t.txn_id_normalized)} />
              ))}
            </div>
        }
      </SectionCard>
    </div>
  );
};

// ---------------------------------------------------------------------------
// InvestigationExplorer — main
// ---------------------------------------------------------------------------
const InvestigationExplorer: React.FC = () => {
  const { data } = useFilterStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [submitted, setSubmitted] = useState('');

  if (!data) return null;

  // Pre-built lookup maps for O(1) access
  const txnMap    = useMemo(() => new Map(data.transactions.map(t => [t.txn_id_normalized, t])), [data]);
  const userMap   = useMemo(() => new Map(data.users.map(u => [u.user_id_normalized, u])), [data]);
  const merchantMap = useMemo(() => new Map(data.merchants.map(m => [m.merchant_id_normalized, m])), [data]);
  const clusterMap  = useMemo(() => new Map(data.clusters.map(c => [c.cluster_id, c])), [data]);
  const chargebackMap = useMemo(() => new Map(data.chargebacks.map(cb => [cb.txn_id_normalized, cb])), [data]);

  // Build user→transactions and merchant→transactions indexes
  const txnsByUser     = useMemo(() => {
    const m = new Map<string, Transaction[]>();
    for (const t of data.transactions) {
      if (!m.has(t.user_id_normalized)) m.set(t.user_id_normalized, []);
      m.get(t.user_id_normalized)!.push(t);
    }
    return m;
  }, [data]);

  const txnsByMerchant = useMemo(() => {
    const m = new Map<string, Transaction[]>();
    for (const t of data.transactions) {
      if (!m.has(t.merchant_id_normalized)) m.set(t.merchant_id_normalized, []);
      m.get(t.merchant_id_normalized)!.push(t);
    }
    return m;
  }, [data]);

  // Resolve search
  const result = useMemo(() => {
    const q = submitted.trim().toUpperCase();
    if (!q) return null;

    if (q.startsWith('CLU')) {
      const cluster = clusterMap.get(q);
      if (!cluster) return { type: 'notfound', query: q };
      const members = data.clusterMembers[q] ?? { users: [], merchants: [] };
      const users = members.users.map(id => userMap.get(id)).filter(Boolean) as typeof data.users;
      const merchants = members.merchants.map(id => merchantMap.get(id)).filter(Boolean) as typeof data.merchants;
      // Get all transactions for all member users
      const memberUserSet = new Set(members.users);
      const transactions = data.transactions.filter(t => memberUserSet.has(t.user_id_normalized));
      return { type: 'cluster', cluster, users, merchants, transactions };
    }

    if (q.startsWith('TXN')) {
      const txn = txnMap.get(q);
      if (!txn) return { type: 'notfound', query: q };
      const user = userMap.get(txn.user_id_normalized);
      const merchant = merchantMap.get(txn.merchant_id_normalized);
      const chargeback = chargebackMap.get(q);
      return { type: 'transaction', txn, user, merchant, chargeback };
    }

    if (q.startsWith('USR')) {
      const user = userMap.get(q);
      if (!user) return { type: 'notfound', query: q };
      const transactions = txnsByUser.get(q) ?? [];
      return { type: 'user', user, transactions };
    }

    if (q.startsWith('MCH')) {
      const merchant = merchantMap.get(q);
      if (!merchant) return { type: 'notfound', query: q };
      const transactions = txnsByMerchant.get(q) ?? [];
      return { type: 'merchant', merchant, transactions };
    }

    return { type: 'unknown', query: q };
  }, [submitted, clusterMap, txnMap, userMap, merchantMap, chargebackMap, data, txnsByUser, txnsByMerchant]);

  const handleSearch = () => setSubmitted(searchTerm.trim());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Search className="text-blue-500" /> Investigation Explorer
        </h2>
        <p className="text-slate-400 mt-1">
          Search by Cluster ID (CLUxxxxx), Transaction ID (TXNxxxxx), User ID (USRxxxxx), or Merchant ID (MCHxxxxx).
          Evidence comes from M3–M7 authoritative outputs only.
        </p>
      </div>

      {/* Search input */}
      <div className="max-w-2xl flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 text-slate-500" size={16} />
          <input
            type="text"
            placeholder="e.g. CLU00604  ·  TXN00011869  ·  USR40970  ·  MCH6502"
            className="w-full bg-slate-800 border border-slate-700 rounded-md py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-semibold transition-colors"
        >
          Investigate
        </button>
      </div>

      {/* Results */}
      {result?.type === 'cluster' && (
        <ClusterDetail
          cluster={result.cluster!}
          users={result.users!}
          merchants={result.merchants!}
          transactions={result.transactions!}
          chargebackMap={chargebackMap}
        />
      )}

      {result?.type === 'transaction' && (
        <TransactionDetail
          txn={result.txn!}
          user={result.user}
          merchant={result.merchant}
          chargeback={result.chargeback}
        />
      )}

      {result?.type === 'user' && (
        <UserDetail
          user={result.user!}
          transactions={result.transactions!}
          chargebackMap={chargebackMap}
        />
      )}

      {result?.type === 'merchant' && (
        <MerchantDetail
          merchant={result.merchant!}
          transactions={result.transactions!}
          chargebackMap={chargebackMap}
        />
      )}

      {result?.type === 'notfound' && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center">
          <p className="text-slate-400">No entity found matching <span className="font-mono text-white">{result.query}</span>.</p>
          <p className="text-xs text-slate-600 mt-1">Only IDs from authoritative M3–M7 outputs are valid.</p>
        </div>
      )}

      {result?.type === 'unknown' && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center">
          <p className="text-slate-400">
            Unrecognised ID format. Use CLUxxxxx, TXNxxxxx, USRxxxxx, or MCHxxxxx.
          </p>
        </div>
      )}
    </div>
  );
};

export default InvestigationExplorer;
