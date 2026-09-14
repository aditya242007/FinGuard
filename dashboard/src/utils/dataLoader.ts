/**
 * dataLoader.ts
 * =============
 * Loads pre-joined, dashboard-ready JSON files produced by
 * scripts/prepare_dashboard_data.py.
 *
 * IMPORTANT: All source data originates from M3–M7 processed outputs.
 * Business logic is NOT redefined here.
 */

// ---------------------------------------------------------------------------
// Interfaces (matching slim JSON schema from prepare_dashboard_data.py)
// ---------------------------------------------------------------------------

export interface Transaction {
  // Identity
  txn_id_normalized: string;
  timestamp_clean: string;
  user_id_normalized: string;
  merchant_id_normalized: string;

  // Amount — authoritative signed amount (amount_numeric from M2)
  amount_numeric: number;

  // Status
  status_clean: string;          // "SUCCESS" | "FAILED" | "PENDING"

  // Classification
  merchant_category_clean: string;
  kyc_status_clean: string;      // "VERIFIED" | "UNVERIFIED" | "UNKNOWN"

  // Chargeback
  has_chargeback: boolean;
  chargeback_count: number;
  total_disputed_amount: number;
  dispute_after_7_days_flag: boolean;

  // Data-quality flags (from M2)
  utr_missing_flag: boolean;
  amount_negative_flag: boolean;
  transaction_has_kyc: boolean;
  transaction_has_merchant: boolean;

  // M6 Risk Scores — transaction-time (point-in-time signals)
  transaction_time_risk_score: number;
  transaction_time_risk_level: string;  // LOW | MEDIUM | HIGH | CRITICAL

  // M6 Risk Scores — retrospective (full-history signals)
  retrospective_risk_score: number;
  retrospective_risk_level: string;

  // M6 Explainability
  explanation: string;
  top_risk_signal_1: string;
  top_risk_signal_2: string;
  top_risk_signal_3: string;
}

export interface UserAnalytics {
  user_id_normalized: string;
  transaction_count: number;
  total_transaction_amount: number;
  successful_transaction_count: number;
  failed_transaction_count: number;
  chargeback_count: number;
  total_disputed_amount: number;
  avg_transaction_amount: number;
  kyc_status_clean: string;
  kyc_match_flag: boolean;

  // M6
  retrospective_risk_score: number;
  risk_level: string;
  explanation: string;
  top_risk_signal_1: string;
  top_risk_signal_2: string;
  top_risk_signal_3: string;
}

export interface MerchantAnalytics {
  merchant_id_normalized: string;
  transaction_count: number;
  total_transaction_amount: number;
  successful_transaction_count: number;
  failed_transaction_count: number;
  chargeback_count: number;
  total_disputed_amount: number;
  avg_transaction_amount: number;
  chargeback_rate: number;
  disputed_amount_ratio: number;
  success_rate: number;
  failure_rate: number;
  merchant_status_clean: string;
  merchant_category_clean: string;

  // M6
  retrospective_risk_score: number;
  risk_level: string;
  explanation: string;
  top_risk_signal_1: string;
  top_risk_signal_2: string;
  top_risk_signal_3: string;
}

export interface SuspiciousCluster {
  cluster_id: string;
  n_users: number;
  n_merchants: number;
  n_transactions: number;
  transaction_amount: number;
  chargeback_count: number;                   // raw complaint record count
  chargebacked_transaction_count: number;
  cluster_chargeback_rate: number;            // <= 1.0 always
  disputed_amount: number;
  disputed_amount_ratio: number;
  cluster_risk_score: number;
  risk_level: string;
  top_signals: string;
  explanation: string;
}

export interface ClusterMembers {
  [cluster_id: string]: {
    users: string[];
    merchants: string[];
  };
}

export interface ChargebackRecord {
  txn_id_normalized: string;
  chargeback_count: number;
  total_disputed_amount: number;
  max_severity: string;
  first_chargeback_timestamp: string;
  latest_chargeback_timestamp: string;
}

export interface GlobalData {
  transactions: Transaction[];
  users: UserAnalytics[];
  merchants: MerchantAnalytics[];
  clusters: SuspiciousCluster[];
  clusterMembers: ClusterMembers;
  chargebacks: ChargebackRecord[];
}

// ---------------------------------------------------------------------------
// Loader
// ---------------------------------------------------------------------------

async function loadJson<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status} ${resp.statusText}`);
  return resp.json() as Promise<T>;
}

export async function fetchAllData(): Promise<GlobalData> {
  const [transactions, users, merchants, clusters, clusterMembers, chargebacks] =
    await Promise.all([
      loadJson<Transaction[]>('/data/finguard_transactions_slim.json'),
      loadJson<UserAnalytics[]>('/data/users_slim.json'),
      loadJson<MerchantAnalytics[]>('/data/merchants_slim.json'),
      loadJson<SuspiciousCluster[]>('/data/clusters_slim.json'),
      loadJson<ClusterMembers>('/data/cluster_members_map.json'),
      loadJson<ChargebackRecord[]>('/data/chargebacks_slim.json'),
    ]);

  return { transactions, users, merchants, clusters, clusterMembers, chargebacks };
}
