import Papa from 'papaparse';

export async function loadCsvData<T>(filePath: string): Promise<T[]> {
  return new Promise((resolve, reject) => {
    Papa.parse(filePath, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        resolve(results.data as T[]);
      },
      error: (error: any) => {
        reject(error);
      }
    });
  });
}

// Interfaces based on data contracts
export interface Transaction {
  txn_id_normalized: string;
  transaction_date: string;
  transaction_hour: number;
  amount_numeric: number;
  amount_abs: number;
  status_clean: string;
  merchant_category_clean: string;
  kyc_status_clean: string;
  has_chargeback: boolean | number;
  chargeback_count: number;
  total_disputed_amount: number;
  transaction_time_risk_score?: number;
  transaction_time_risk_level?: string;
  retrospective_risk_score?: number;
  retrospective_risk_level?: string;
  user_id_normalized: string;
  merchant_id_normalized: string;
  missing_utr_flag?: boolean | number;
  kyc_match_flag?: boolean | number;
  merchant_match_flag?: boolean | number;
}

export interface UserAnalytics {
  user_id_normalized: string;
  transaction_count: number;
  total_transaction_amount: number;
  chargeback_rate: number;
  total_disputed_amount: number;
  success_rate: number;
  failure_rate: number;
  kyc_status_clean: string;
  risk_level?: string;
  retrospective_risk_score?: number;
}

export interface MerchantAnalytics {
  merchant_id_normalized: string;
  transaction_count: number;
  total_transaction_amount: number;
  chargeback_rate: number;
  disputed_amount_ratio: number;
  success_rate: number;
  failure_rate: number;
  merchant_category_clean: string;
  merchant_status_clean: string;
  risk_level?: string;
  retrospective_risk_score?: number;
}

export interface SuspiciousCluster {
  cluster_id: string;
  cluster_risk_score: number;
  risk_level: string;
  n_users: number;
  n_merchants: number;
  n_transactions: number;
  chargeback_count: number;
  chargebacked_transaction_count: number;
  cluster_chargeback_rate: number;
  disputed_amount: number;
  disputed_amount_ratio: number;
  top_signals: string;
  explanation: string;
}

export interface GlobalData {
  transactions: Transaction[];
  users: UserAnalytics[];
  merchants: MerchantAnalytics[];
  clusters: SuspiciousCluster[];
}

export async function fetchAllData(): Promise<GlobalData> {
  const [
    transactions,
    usersAnalytics,
    merchantsAnalytics,
    userScores,
    merchantScores,
    clusters
  ] = await Promise.all([
    loadCsvData<any>('/data/finguard_transactions.csv'),
    loadCsvData<any>('/data/users_analytics.csv'),
    loadCsvData<any>('/data/merchants_analytics.csv'),
    loadCsvData<any>('/data/user_risk_scores.csv').catch(() => []), // Optional catch
    loadCsvData<any>('/data/merchant_risk_scores.csv').catch(() => []),
    loadCsvData<any>('/data/suspicious_clusters.csv')
  ]);

  // Merge risk scores into analytics
  const userScoreMap = new Map(userScores.map(u => [u.user_id, u]));
  const mergedUsers = usersAnalytics.map(u => {
    const score = userScoreMap.get(u.user_id_normalized);
    return {
      ...u,
      risk_level: score?.risk_level,
      retrospective_risk_score: score?.retrospective_risk_score
    } as UserAnalytics;
  });

  const merchantScoreMap = new Map(merchantScores.map(m => [m.merchant_id, m]));
  const mergedMerchants = merchantsAnalytics.map(m => {
    const score = merchantScoreMap.get(m.merchant_id_normalized);
    return {
      ...m,
      risk_level: score?.risk_level,
      retrospective_risk_score: score?.retrospective_risk_score
    } as MerchantAnalytics;
  });

  return {
    transactions: transactions as Transaction[],
    users: mergedUsers,
    merchants: mergedMerchants,
    clusters: clusters as SuspiciousCluster[]
  };
}
