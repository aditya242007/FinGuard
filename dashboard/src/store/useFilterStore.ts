/**
 * useFilterStore.ts
 * =================
 * Global Zustand filter store for the FinGuard dashboard.
 * All 8 required filter dimensions are implemented here.
 */
import { create } from 'zustand';
import { fetchAllData } from '../utils/dataLoader';
import type { GlobalData, Transaction } from '../utils/dataLoader';

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface FilterState {
  // Global Data
  data: GlobalData | null;
  isLoading: boolean;
  error: string | null;

  // Filter Dimensions (all 8 required)
  dateStart: string | null;        // ISO date string "YYYY-MM-DD"
  dateEnd: string | null;
  status: string | null;           // "SUCCESS" | "FAILED" | "PENDING"
  merchantCategory: string | null;
  merchantId: string | null;
  userId: string | null;
  riskLevel: string | null;        // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  hasChargeback: boolean | null;
  kycStatus: string | null;        // "VERIFIED" | "UNVERIFIED" | "UNKNOWN"

  // Derived: filtered transactions (computed on filter change)
  filteredTransactions: Transaction[];

  // Actions
  loadData: () => Promise<void>;
  setFilter: (
    key: keyof Omit<FilterState, 'data' | 'isLoading' | 'error' | 'filteredTransactions' | 'loadData' | 'setFilter' | 'resetFilters'>,
    value: unknown
  ) => void;
  resetFilters: () => void;
}

// ---------------------------------------------------------------------------
// Filter logic — single source of truth
// ---------------------------------------------------------------------------

function applyFilters(transactions: Transaction[], state: Partial<FilterState>): Transaction[] {
  return transactions.filter(t => {
    // Date range filter
    if (state.dateStart) {
      const txnDate = t.timestamp_clean?.slice(0, 10) ?? '';
      if (txnDate < state.dateStart) return false;
    }
    if (state.dateEnd) {
      const txnDate = t.timestamp_clean?.slice(0, 10) ?? '';
      if (txnDate > state.dateEnd) return false;
    }

    // Status filter
    if (state.status && t.status_clean !== state.status) return false;

    // Merchant category filter
    if (state.merchantCategory && t.merchant_category_clean !== state.merchantCategory) return false;

    // Merchant ID filter
    if (state.merchantId && t.merchant_id_normalized !== state.merchantId) return false;

    // User ID filter
    if (state.userId && t.user_id_normalized !== state.userId) return false;

    // Risk level filter (uses transaction_time_risk_level from M6)
    if (state.riskLevel && t.transaction_time_risk_level !== state.riskLevel) return false;

    // Chargeback presence filter
    if (state.hasChargeback !== null && state.hasChargeback !== undefined) {
      if (Boolean(t.has_chargeback) !== state.hasChargeback) return false;
    }

    // KYC status filter
    if (state.kycStatus && t.kyc_status_clean !== state.kycStatus) return false;

    return true;
  });
}

// ---------------------------------------------------------------------------
// Default filter values
// ---------------------------------------------------------------------------

const DEFAULT_FILTERS = {
  dateStart: null,
  dateEnd: null,
  status: null,
  merchantCategory: null,
  merchantId: null,
  userId: null,
  riskLevel: null,
  hasChargeback: null,
  kycStatus: null,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useFilterStore = create<FilterState>((set) => ({
  data: null,
  isLoading: true,
  error: null,
  filteredTransactions: [],
  ...DEFAULT_FILTERS,

  loadData: async () => {
    try {
      set({ isLoading: true, error: null });
      const data = await fetchAllData();
      set({
        data,
        isLoading: false,
        filteredTransactions: data.transactions,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      set({ error: message, isLoading: false });
    }
  },

  setFilter: (key, value) => {
    set(state => {
      const updated = { ...state, [key]: value };
      const filteredTransactions = state.data
        ? applyFilters(state.data.transactions, updated)
        : [];
      return { ...updated, filteredTransactions };
    });
  },

  resetFilters: () => {
    set(state => ({
      ...DEFAULT_FILTERS,
      filteredTransactions: state.data ? state.data.transactions : [],
    }));
  },
}));
