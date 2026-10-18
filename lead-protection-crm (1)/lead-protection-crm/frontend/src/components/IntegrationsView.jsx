import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  CreditCard,
  Calendar,
  Bell,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Send,
  Activity,
  ShieldCheck,
  ShieldAlert,
  Code,
  Zap,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  ChevronLeft,
  ChevronRight,
  Info
} from 'lucide-react';

const API_BASE = '/api/v1';

export default function IntegrationsView({ token, onError, onSuccess }) {
  const [loading, setLoading] = useState(true);
  const [testingProvider, setTestingProvider] = useState(null);
  const [statusData, setStatusData] = useState(null);
  
  // Sync history state
  const [syncHistory, setSyncHistory] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  // Simulator state
  const [waSim, setWaSim] = useState({
    sender: '+919876543210',
    name: 'Pooja Mehta',
    text: 'Hello, looking for a 3BHK commercial property in Bandra.'
  });
  const [paySim, setPaySim] = useState({
    gateway: 'mock-payment',
    event_id: `evt_${Date.now()}`,
    amount: 15000,
    currency: 'INR'
  });
  const [simLoading, setSimLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/integrations/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      let url = `${API_BASE}/integrations/sync-history?page=${historyPage}&limit=12`;
      if (typeFilter) url += `&provider_type=${typeFilter}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSyncHistory(data.items || []);
        setHistoryTotal(data.total || 0);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const refreshAll = async () => {
    setLoading(true);
    await Promise.all([fetchStatus(), fetchHistory()]);
    setLoading(false);
  };

  useEffect(() => {
    refreshAll();
  }, [token, historyPage, typeFilter, statusFilter]);

  const handleTestConnection = async (type) => {
    setTestingProvider(type);
    try {
      const res = await fetch(`${API_BASE}/integrations/test/${type}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await res.json();
      if (res.ok) {
        onSuccess?.(`Test successful for ${type} (${data.provider})`);
        fetchStatus();
        fetchHistory();
      } else {
        onError?.(data.detail || `Test failed for ${type}`);
      }
    } catch (err) {
      onError?.(err.message);
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSimulateWhatsApp = async (e) => {
    e.preventDefault();
    setSimLoading(true);
    try {
      const res = await fetch(`${API_BASE}/webhooks/whatsapp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Signature': 'valid_mock_token'
        },
        body: JSON.stringify({
          from: waSim.sender,
          name: waSim.name,
          body: waSim.text,
          message_id: `sim_wa_${Date.now()}`
        })
      });
      const data = await res.json();
      if (res.ok) {
        onSuccess?.(`WhatsApp webhook delivered! Status: ${data.status}`);
        fetchStatus();
        fetchHistory();
      } else {
        onError?.(data.detail || 'Simulation error');
      }
    } catch (err) {
      onError?.(err.message);
    } finally {
      setSimLoading(false);
    }
  };

  const handleSimulatePayment = async (e) => {
    e.preventDefault();
    setSimLoading(true);
    try {
      const endpoint = paySim.gateway === 'stripe' ? '/webhooks/stripe' :
                       paySim.gateway === 'razorpay' ? '/webhooks/razorpay' :
                       '/webhooks/mock-payment';
      
      const payload = paySim.gateway === 'stripe' ? {
        id: paySim.event_id,
        type: 'checkout.session.completed',
        data: {
          object: {
            id: `cs_${Date.now()}`,
            amount_total: paySim.amount * 100,
            currency: paySim.currency.toLowerCase(),
            payment_status: 'paid'
          }
        }
      } : {
        event_id: paySim.event_id,
        payment_id: `pay_${Date.now()}`,
        amount: paySim.amount,
        currency: paySim.currency,
        status: 'paid'
      };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Signature': 'valid'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        onSuccess?.(`Payment webhook handled! Status: ${data.status}`);
        setPaySim(prev => ({ ...prev, event_id: `evt_${Date.now()}` }));
        fetchStatus();
        fetchHistory();
      } else {
        onError?.(data.detail || 'Payment simulation failed');
      }
    } catch (err) {
      onError?.(err.message);
    } finally {
      setSimLoading(false);
    }
  };

  const getProviderIcon = (type) => {
    switch (type) {
      case 'messaging': return <MessageSquare className="w-5 h-5 text-emerald-400" />;
      case 'payment': return <CreditCard className="w-5 h-5 text-indigo-400" />;
      case 'calendar': return <Calendar className="w-5 h-5 text-amber-400" />;
      case 'notify': return <Bell className="w-5 h-5 text-rose-400" />;
      default: return <Activity className="w-5 h-5 text-slate-400" />;
    }
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return 'Never';
    try {
      const normalizedIso = (typeof isoStr === 'string' && !isoStr.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(isoStr))
        ? `${isoStr}Z`
        : isoStr;
      const dt = new Date(normalizedIso);
      return dt.toLocaleString(undefined, {
        dateStyle: 'short',
        timeStyle: 'medium'
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="p-2 rounded-xl bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 text-indigo-400 border border-indigo-500/30">
              <Zap className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-white">Provider Adapters & Sync Observability</h2>
          </div>
          <p className="text-xs text-slate-400 max-w-2xl">
            Plug-and-play adapter layer configured via environment variables. Each adapter features cryptographic webhook validation, idempotency checks, backoff retries, and failure isolation so downtime in one provider never halts CRM operations.
          </p>
        </div>

        <button
          onClick={refreshAll}
          disabled={loading}
          className="self-start md:self-auto px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-2 transition border border-slate-700/60 shadow"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          Refresh Status
        </button>
      </div>

      {/* 4 Provider Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statusData && Object.entries(statusData).map(([key, prov]) => (
          <div key={key} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-slate-700 transition">
            <div>
              {/* Card Header */}
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/50">
                    {getProviderIcon(key)}
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">
                      {key}
                    </span>
                    <span className="text-sm font-semibold text-white tracking-tight">
                      {prov.provider_name}
                    </span>
                  </div>
                </div>

                {/* MOCK vs LIVE vs Not configured Badge */}
                {prov.is_mock ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/10">
                    MOCK
                  </span>
                ) : !prov.is_configured ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm shadow-rose-500/10">
                    live
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/10">
                    LIVE
                  </span>
                )}
              </div>

              {/* Plain-Language Limits Note */}
              <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 mb-4">
                <div className="flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
                    {prov.limits_note}
                  </p>
                </div>
              </div>

              {/* Telemetry Metrics */}
              <div className="space-y-2 text-xs mb-4">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Last Success:</span>
                  <span className="text-slate-200 font-mono text-[11px]">
                    {formatTime(prov.last_success_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Last Error:</span>
                  <span className={`font-mono text-[11px] ${prov.last_error_at ? 'text-rose-400' : 'text-slate-500'}`}>
                    {prov.last_error_at ? formatTime(prov.last_error_at) : 'None (Healthy)'}
                  </span>
                </div>
                {prov.last_error_message && (
                  <div className="p-2 rounded bg-rose-950/40 border border-rose-900/50 text-rose-300 text-[10px] truncate">
                    {prov.last_error_message}
                  </div>
                )}
                <div className="flex items-center justify-between text-slate-400 pt-1 border-t border-slate-800/60">
                  <span>Total Calls / Health:</span>
                  <span className="font-semibold text-slate-200">
                    {prov.total_calls} calls • <span className="text-emerald-400">{prov.success_rate}%</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Test Connection Button */}
            <button
              onClick={() => handleTestConnection(key)}
              disabled={testingProvider === key}
              className="w-full py-2 rounded-xl bg-slate-800 hover:bg-indigo-600/30 hover:border-indigo-500/40 text-slate-200 hover:text-white border border-slate-700/60 text-xs font-semibold flex items-center justify-center gap-2 transition"
            >
              {testingProvider === key ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                  Testing...
                </>
              ) : (
                <>
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                  Test Connection
                </>
              )}
            </button>
          </div>
        ))}
      </div>

      {/* Simulator Section (for instant testing of webhooks and flows) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* WhatsApp Simulator */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Interactive WhatsApp Inbound Webhook Simulator</h3>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Simulate a customer texting your business WhatsApp number. Tests webhook parsing, signature verification, and sync log idempotency.
          </p>
          <form onSubmit={handleSimulateWhatsApp} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-semibold text-slate-400 block mb-1">Customer Phone</label>
                <input
                  type="text"
                  value={waSim.sender}
                  onChange={(e) => setWaSim({ ...waSim, sender: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-400 block mb-1">Customer Name</label>
                <input
                  type="text"
                  value={waSim.name}
                  onChange={(e) => setWaSim({ ...waSim, name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                  required
                />
              </div>
            </div>
            <div>
              <label className="text-[10px] font-semibold text-slate-400 block mb-1">Message Text</label>
              <textarea
                value={waSim.text}
                onChange={(e) => setWaSim({ ...waSim, text: e.target.value })}
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white resize-none"
                required
              />
            </div>
            <button
              type="submit"
              disabled={simLoading}
              className="w-full py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition shadow-lg shadow-emerald-600/20"
            >
              <Send className="w-3.5 h-3.5" />
              Send Inbound WhatsApp Webhook
            </button>
          </form>
        </div>

        {/* Payment Webhook Simulator */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-bold text-white">Payment Webhook & Idempotency Simulator</h3>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Emulate payment gateway webhook callbacks. Resending the same Event ID demonstrates idempotency deduplication.
          </p>
          <form onSubmit={handleSimulatePayment} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-semibold text-slate-400 block mb-1">Gateway Endpoint</label>
                <select
                  value={paySim.gateway}
                  onChange={(e) => setPaySim({ ...paySim, gateway: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                >
                  <option value="mock-payment">Mock Checkout (/webhooks/mock-payment)</option>
                  <option value="stripe">Stripe Test (/webhooks/stripe)</option>
                  <option value="razorpay">Razorpay Test (/webhooks/razorpay)</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-400 block mb-1">Amount & Currency</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={paySim.amount}
                    onChange={(e) => setPaySim({ ...paySim, amount: parseFloat(e.target.value) || 0 })}
                    className="w-2/3 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                    required
                  />
                  <input
                    type="text"
                    value={paySim.currency}
                    onChange={(e) => setPaySim({ ...paySim, currency: e.target.value })}
                    className="w-1/3 bg-slate-950 border border-slate-800 rounded-xl px-2 py-1.5 text-xs text-white text-center font-bold"
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="text-[10px] font-semibold text-slate-400 block mb-1">Event ID (Idempotency Key)</label>
              <input
                type="text"
                value={paySim.event_id}
                onChange={(e) => setPaySim({ ...paySim, event_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs font-mono text-white"
                required
              />
            </div>
            <button
              type="submit"
              disabled={simLoading}
              className="w-full py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-600/20"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Trigger Payment Webhook
            </button>
          </form>
        </div>
      </div>

      {/* Sync History Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              Live Sync History & Audit Log
            </h3>
            <p className="text-xs text-slate-400">
              Immutable record of all inbound webhooks and outbound API calls across providers.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setHistoryPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300"
            >
              <option value="">All Categories</option>
              <option value="messaging">Messaging</option>
              <option value="payment">Payment</option>
              <option value="calendar">Calendar</option>
              <option value="notify">Notify</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setHistoryPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300"
            >
              <option value="">All Statuses</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto border border-slate-800/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Provider</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Direction</th>
                <th className="py-3 px-4">Event ID</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {syncHistory.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 text-xs">
                    No sync records found for the selected filter. Trigger a test connection or simulated webhook above.
                  </td>
                </tr>
              ) : (
                syncHistory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">
                      {formatTime(item.created_at)}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-slate-200">
                      <span className="capitalize">{item.provider_name.replace('_', ' ')}</span>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-slate-300">
                      {item.action}
                    </td>
                    <td className="py-2.5 px-4">
                      {item.direction === 'inbound' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          <ArrowDownLeft className="w-3 h-3" />
                          INBOUND
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          <ArrowUpRight className="w-3 h-3" />
                          OUTBOUND
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-400 truncate max-w-[140px]">
                      {item.event_id || '—'}
                    </td>
                    <td className="py-2.5 px-4">
                      {item.status === 'success' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" />
                          {item.status_code || 200}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          <AlertTriangle className="w-3 h-3" />
                          {item.status_code || 500}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-400">
                      {item.latency_ms} ms
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedLog(item)}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-medium transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400">
          <span>Total: {historyTotal} records</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setHistoryPage(p => Math.max(1, p - 1))}
              disabled={historyPage === 1}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-slate-200">Page {historyPage}</span>
            <button
              onClick={() => setHistoryPage(p => p + 1)}
              disabled={syncHistory.length < 12}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Inspect Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full shadow-2xl">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Code className="w-5 h-5 text-indigo-400" />
                Sync Telemetry Payload Inspect
              </h3>
              <button onClick={() => setSelectedLog(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1 text-xs">
              <div className="grid grid-cols-2 gap-4 bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">Provider</span>
                  <span className="font-semibold text-slate-200">{selectedLog.provider_name} ({selectedLog.provider_type})</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">Action / Direction</span>
                  <span className="font-semibold text-slate-200">{selectedLog.action} • {selectedLog.direction}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">Event ID</span>
                  <span className="font-mono text-slate-300">{selectedLog.event_id || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">Latency</span>
                  <span className="font-mono text-emerald-400">{selectedLog.latency_ms} ms</span>
                </div>
              </div>

              {selectedLog.error_message && (
                <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-xl text-rose-300">
                  <span className="font-bold block text-[10px] uppercase mb-1">Error Message</span>
                  {selectedLog.error_message}
                </div>
              )}

              <div>
                <span className="font-bold text-slate-300 block mb-1">Request Payload Summary:</span>
                <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-slate-300 overflow-x-auto">
                  {JSON.stringify(selectedLog.payload_summary, null, 2)}
                </pre>
              </div>

              <div>
                <span className="font-bold text-slate-300 block mb-1">Response Summary:</span>
                <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-slate-300 overflow-x-auto">
                  {JSON.stringify(selectedLog.response_summary, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
