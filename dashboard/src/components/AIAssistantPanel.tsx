import React, { useState } from 'react';
import { Bot, Send, User, AlertTriangle, Sparkles, Loader2 } from 'lucide-react';

interface Message {
  sender: 'user' | 'agent';
  text: string;
  error?: boolean;
}

export const AIAssistantPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'agent',
      text: "Hello! I am **FINguard AI**, your risk intelligence assistant. Ask me to investigate any cluster (e.g. `CLU00604`), user (e.g. `USR40970`), merchant (e.g. `MCH6502`), or transaction (e.g. `TXN00011869`)."
    }
  ]);

  const handleSend = async () => {
    if (!query.trim() || loading) return;
    
    const userMsg = query.trim();
    setQuery('');
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg })
      });

      const data = await res.json();
      if (data.error) {
        setMessages(prev => [...prev, { sender: 'agent', text: `Error: ${data.error}`, error: true }]);
      } else {
        setMessages(prev => [...prev, { sender: 'agent', text: data.response }]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'agent',
          text: "Could not connect to AI Agent API. Please ensure the backend is running on `http://localhost:8000` via `./start_platform.sh`.",
          error: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(prev => !prev)}
        className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-500 text-white p-3.5 rounded-full shadow-lg border border-blue-400/30 flex items-center gap-2 z-50 transition-all duration-200"
      >
        <Sparkles size={20} />
        <span className="font-semibold text-sm">AI Investigator</span>
      </button>

      {/* Drawer / Slide-out Panel */}
      {isOpen && (
        <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="text-blue-400" size={24} />
              <div>
                <h3 className="font-bold text-slate-100 text-sm tracking-wide">FINguard AI Investigator</h3>
                <p className="text-xs text-slate-400">Grounded Risk Intelligence</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-slate-200 text-sm font-semibold px-2 py-1 rounded bg-slate-800/50"
            >
              ✕ Close
            </button>
          </div>

          {/* Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.sender === 'agent' && (
                  <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0">
                    <Bot size={16} className="text-blue-400" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-lg p-3 ${
                    msg.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : msg.error
                      ? 'bg-red-950/60 border border-red-800/50 text-red-200'
                      : 'bg-slate-800 border border-slate-700/60 text-slate-200'
                  }`}
                >
                  {msg.error && <AlertTriangle size={14} className="inline mr-1 text-red-400" />}
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>
                </div>

                {msg.sender === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
                    <User size={16} className="text-slate-300" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start items-center text-slate-400">
                <Loader2 size={16} className="animate-spin text-blue-400" />
                <span className="text-xs">Analyzing grounded dataset...</span>
              </div>
            )}
          </div>

          {/* Input Footer */}
          <div className="p-3 border-t border-slate-800 bg-slate-950 flex gap-2">
            <input
              type="text"
              placeholder="e.g. Investigate cluster CLU00604"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={loading || !query.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded-md font-semibold text-sm flex items-center justify-center transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
