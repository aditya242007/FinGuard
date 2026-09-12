import { create } from 'zustand';
import { fetchAllData } from '../utils/dataLoader';
import type { GlobalData } from '../utils/dataLoader';

interface FilterState {
  // Global Data
  data: GlobalData | null;
  isLoading: boolean;
  error: string | null;
  
  // Filters
  dateRange: [string | null, string | null];
  status: string | null;
  merchantCategory: string | null;
  riskLevel: string | null;
  hasChargeback: boolean | null;
  
  // Actions
  loadData: () => Promise<void>;
  setFilter: (key: keyof Omit<FilterState, 'data' | 'isLoading' | 'error' | 'loadData' | 'setFilter' | 'resetFilters'>, value: any) => void;
  resetFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  data: null,
  isLoading: true,
  error: null,
  
  dateRange: [null, null],
  status: null,
  merchantCategory: null,
  riskLevel: null,
  hasChargeback: null,

  loadData: async () => {
    try {
      set({ isLoading: true, error: null });
      const data = await fetchAllData();
      set({ data, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load data', isLoading: false });
    }
  },

  setFilter: (key, value) => set((state) => ({ ...state, [key]: value })),
  
  resetFilters: () => set({
    dateRange: [null, null],
    status: null,
    merchantCategory: null,
    riskLevel: null,
    hasChargeback: null,
  }),
}));
