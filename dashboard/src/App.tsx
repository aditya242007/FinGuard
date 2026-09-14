import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useFilterStore } from './store/useFilterStore';
import { FilterBar } from './components/FilterBar';
import { AIAssistantPanel } from './components/AIAssistantPanel';
import { Shield, LayoutDashboard, Store, Search, AlertTriangle } from 'lucide-react';

// Placeholder Pages (will be implemented next)
import Overview from './pages/Overview';
import RiskIntelligence from './pages/RiskIntelligence';
import MerchantIntelligence from './pages/MerchantIntelligence';
import InvestigationExplorer from './pages/InvestigationExplorer';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 flex items-center gap-3">
          <Shield className="text-blue-500" size={28} />
          <div>
            <h1 className="font-bold text-lg tracking-tight">FinGuard</h1>
            <p className="text-xs text-slate-400">Risk Intelligence</p>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          <NavLink 
            to="/" 
            className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600/20 text-blue-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </NavLink>
          <NavLink 
            to="/risk" 
            className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600/20 text-blue-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <AlertTriangle size={18} />
            <span>Fraud & Risk</span>
          </NavLink>
          <NavLink 
            to="/merchants" 
            className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600/20 text-blue-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <Store size={18} />
            <span>Merchants</span>
          </NavLink>
          <NavLink 
            to="/investigate" 
            className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600/20 text-blue-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <Search size={18} />
            <span>Investigate</span>
          </NavLink>
        </nav>
        
        <div className="p-4 border-t border-slate-800">
          <div className="bg-slate-800/50 p-3 rounded-md border border-slate-700/50">
            <p className="text-xs text-slate-400 leading-tight">
              Risk scores represent behavioral signals. They are not confirmed fraud probabilities.
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <FilterBar />
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
      <AIAssistantPanel />
    </div>
  );
};

const App: React.FC = () => {
  const { loadData, isLoading, error } = useFilterStore();

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <Shield className="text-blue-500 animate-pulse" size={48} />
          <h2 className="text-xl font-semibold tracking-tight">Loading FinGuard Data...</h2>
          <p className="text-sm text-slate-400">Parsing authoritative datasets from memory</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-slate-100">
        <div className="bg-red-950 border border-red-800 p-6 rounded-lg max-w-md">
          <h2 className="text-xl font-bold text-red-400 mb-2 flex items-center gap-2">
            <AlertTriangle /> Data Load Failed
          </h2>
          <p className="text-slate-300 mb-4">{error}</p>
          <p className="text-sm text-slate-400">
            Did you run `scripts/prepare_dashboard_data.py` to populate `public/data/`?
          </p>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/risk" element={<RiskIntelligence />} />
          <Route path="/merchants" element={<MerchantIntelligence />} />
          <Route path="/investigate" element={<InvestigationExplorer />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
