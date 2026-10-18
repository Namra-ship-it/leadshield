import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Building2, 
  Users, 
  UserCheck, 
  UserPlus, 
  Lock, 
  KeyRound, 
  AlertTriangle, 
  CheckCircle2, 
  LogOut, 
  RefreshCw,
  Sliders,
  Layers,
  Phone,
  Mail,
  Plus,
  ArrowRight,
  ArrowLeft,
  DollarSign,
  Briefcase,
  ChevronRight,
  Tag,
  Settings2,
  Clock,
  Radio,
  Flame,
  AlertOctagon,
  Send,
  UserX,
  Zap
} from 'lucide-react';
import IntegrationsView from './components/IntegrationsView';

const API_BASE = '/api/v1';

async function parseResponse(res) {
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await res.json();
  }
  const text = await res.text();
  return { detail: text || `HTTP ${res.status}` };
}

const PIPELINE_STAGES = [
  { id: 'new_lead', label: 'New Lead', color: 'border-blue-900/40 bg-blue-900/10 text-blue-900' },
  { id: 'contacted', label: 'Contacted', color: 'border-amber-900/40 bg-amber-900/10 text-amber-900' },
  { id: 'meeting_scheduled', label: 'Meeting Scheduled', color: 'border-purple-900/40 bg-purple-900/10 text-purple-900' },
  { id: 'proposal_sent', label: 'Proposal Sent', color: 'border-[#4C3D19]/40 bg-[#4C3D19]/10 text-[#4C3D19]' },
  { id: 'closed_won', label: 'Closed Won', color: 'border-emerald-900/40 bg-emerald-900/10 text-emerald-900' },
  { id: 'closed_lost', label: 'Closed Lost', color: 'border-[#4C3D19]/40 bg-[#4C3D19]/20 text-[#4C3D19]' }
];

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [activeTab, setActiveTab] = useState('lead_engine'); // 'lead_engine', 'recovery_queue', 'pipeline', 'contacts', 'custom_fields', 'workspace'

  // Data states
  const [teamMembers, setTeamMembers] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [customFields, setCustomFields] = useState([]);
  const [leads, setLeads] = useState([]);
  const [recoveryQueue, setRecoveryQueue] = useState([]);

  // Live timer tick
  const [currentTime, setCurrentTime] = useState(Date.now());

  // UI / feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals
  const [showNewOppModal, setShowNewOppModal] = useState(false);
  const [showNewContactModal, setShowNewContactModal] = useState(false);
  const [showNewFieldModal, setShowNewFieldModal] = useState(false);
  const [showPublicFormModal, setShowPublicFormModal] = useState(false);

  // Auth form states
  const [isLoginMode, setIsLoginMode] = useState(false);
  const [signupForm, setSignupForm] = useState({
    workspace_name: 'Apex Realty',
    full_name: 'Priya Sharma',
    email: 'priya@apexrealty.com',
    password: 'Password123!'
  });
  const [loginForm, setLoginForm] = useState({
    email: 'priya@apexrealty.com',
    password: 'Password123!'
  });

  // Public web form state
  const [publicForm, setPublicForm] = useState({
    full_name: 'Vikram Sethi',
    email: 'vikram@luxuryhomes.in',
    phone: '+919876543210',
    inquiry: 'Interested in a 4BHK penthouse with sea view.'
  });

  // Opportunity form
  const [oppForm, setOppForm] = useState({
    title: '',
    value: 500000,
    currency: 'INR',
    stage: 'new_lead',
    contact_id: '',
    company_id: '',
    assigned_to_id: '',
    custom_fields: {}
  });

  // Contact form
  const [contactForm, setContactForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    company_id: '',
    custom_fields: {}
  });

  // Custom Field Form
  const [fieldForm, setFieldForm] = useState({
    entity_type: 'opportunity',
    label: '',
    field_key: '',
    field_type: 'text',
    optionsStr: 'Residential, Commercial, Industrial'
  });

  // Invite user form
  const [inviteForm, setInviteForm] = useState({
    full_name: '',
    email: '',
    password: 'Password123!',
    role: 'user',
    phone: ''
  });

  // Workspace settings form
  const [settingsForm, setSettingsForm] = useState({
    name: '',
    ackTimeout: 20,
    maxOpenLeads: 5
  });

  // Isolation test state
  const [isolationTargetId, setIsolationTargetId] = useState('');
  const [isolationResult, setIsolationResult] = useState(null);

  // Periodic clock tick for visible timers (every second)
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch initial data
  useEffect(() => {
    if (token) {
      loadAllData();
      // Poll leads every 5 seconds for live demo feel
      const pollTimer = setInterval(() => {
        fetchLeads();
        fetchRecoveryQueue();
        fetchTeam();
      }, 4000);
      return () => clearInterval(pollTimer);
    } else {
      setUser(null);
      setWorkspace(null);
      setTeamMembers([]);
      setCompanies([]);
      setContacts([]);
      setOpportunities([]);
      setCustomFields([]);
      setLeads([]);
      setRecoveryQueue([]);
    }
  }, [token]);

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchProfile(),
      fetchTeam(),
      fetchCompanies(),
      fetchContacts(),
      fetchOpportunities(),
      fetchCustomFields(),
      fetchLeads(),
      fetchRecoveryQueue()
    ]);
    setLoading(false);
  };

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        if (res.status === 401) handleLogout();
        throw new Error('Failed to load profile');
      }
      const data = await res.json();
      setUser(data.user);
      setWorkspace(data.workspace);
      setSettingsForm({
        name: data.workspace.name,
        ackTimeout: data.workspace.settings?.acknowledgement_timeout_seconds || 20,
        maxOpenLeads: data.workspace.settings?.max_open_leads_per_rep || 5
      });
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchTeam = async () => {
    try {
      const res = await fetch(`${API_BASE}/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setTeamMembers(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchLeads = async () => {
    try {
      const res = await fetch(`${API_BASE}/leads`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setLeads(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchRecoveryQueue = async () => {
    try {
      const res = await fetch(`${API_BASE}/leads/recovery-queue`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setRecoveryQueue(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchCompanies = async () => {
    try {
      const res = await fetch(`${API_BASE}/companies`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setCompanies(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchContacts = async () => {
    try {
      const res = await fetch(`${API_BASE}/contacts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setContacts(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchOpportunities = async () => {
    try {
      const res = await fetch(`${API_BASE}/opportunities`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setOpportunities(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchCustomFields = async () => {
    try {
      const res = await fetch(`${API_BASE}/custom-fields`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setCustomFields(await res.json());
    } catch (err) { console.error(err); }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupForm)
      });
      const data = await parseResponse(res);
      if (!res.ok) throw new Error(data?.detail || 'Signup failed');

      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      setWorkspace(data.workspace);
      setSuccessMsg(`Workspace "${data.workspace.name}" created with Owner account!`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });
      const data = await parseResponse(res);
      if (!res.ok) throw new Error(data?.detail || 'Login failed');

      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      setWorkspace(data.workspace);
      setSuccessMsg(`Welcome back, ${data.user.full_name}!`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
    setWorkspace(null);
  };

  // Submit Public Web Form
  const handlePublicLeadSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const payload = {
        workspace_slug: workspace.slug,
        full_name: publicForm.full_name,
        email: publicForm.email || null,
        phone: publicForm.phone || null,
        inquiry: publicForm.inquiry
      };
      const res = await fetch(`${API_BASE}/leads/public`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to submit public lead');

      setSuccessMsg(`New lead "${data.title}" arrived! Assigned with visible countdown timer.`);
      setShowPublicFormModal(false);
      fetchLeads();
      fetchContacts();
      fetchTeam();
    } catch (err) {
      setError(err.message);
    }
  };

  // Acknowledge Lead (Rep takes responsibility)
  const handleAcknowledge = async (leadId) => {
    try {
      const res = await fetch(`${API_BASE}/leads/${leadId}/acknowledge`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to acknowledge lead');

      setSuccessMsg('Lead acknowledged! Countdown timer stopped. Accountability confirmed.');
      fetchLeads();
    } catch (err) {
      setError(err.message);
    }
  };

  // Force Escalate (Demo accelerator)
  const handleForceEscalate = async (leadId) => {
    try {
      const res = await fetch(`${API_BASE}/leads/${leadId}/escalate-now`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Escalation failed');

      setSuccessMsg(`Lead escalated to level ${data.escalation_level}! New owner assigned.`);
      fetchLeads();
      fetchRecoveryQueue();
      fetchTeam();
    } catch (err) {
      setError(err.message);
    }
  };

  // Claim from Recovery Queue
  const handleClaimLead = async (leadId) => {
    try {
      const res = await fetch(`${API_BASE}/leads/${leadId}/claim`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to claim lead');

      setSuccessMsg(`Claimed lead "${data.title}"! You are now the accountable owner.`);
      fetchLeads();
      fetchRecoveryQueue();
    } catch (err) {
      setError(err.message);
    }
  };

  // Toggle Employee Status (e.g. On Leave immediately reassigns leads)
  const handleStatusChange = async (userId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/users/${userId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        if (newStatus === 'on_leave') {
          setSuccessMsg('Status changed to On Leave. All pending leads automatically reassigned to available reps!');
        }
        fetchTeam();
        fetchLeads();
        fetchRecoveryQueue();
        if (user && user.id === userId) setUser(prev => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Update Workspace Settings (timeouts down to seconds)
  const handleUpdateSettings = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/workspaces/current`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: settingsForm.name,
          settings: {
            acknowledgement_timeout_seconds: parseInt(settingsForm.ackTimeout),
            max_open_leads_per_rep: parseInt(settingsForm.maxOpenLeads)
          }
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save settings');
      setWorkspace(data);
      setSuccessMsg('Workspace routing settings updated! Timers configured.');
    } catch (err) {
      setError(err.message);
    }
  };

  // Stage Move
  const handleStageMove = async (oppId, newStage) => {
    try {
      const res = await fetch(`${API_BASE}/opportunities/${oppId}/stage`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ stage: newStage })
      });
      if (res.ok) {
        setOpportunities(prev => prev.map(o => o.id === oppId ? { ...o, stage: newStage } : o));
      }
    } catch (err) { console.error(err); }
  };

  // Create Opportunity
  const handleCreateOpportunity = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        title: oppForm.title,
        value: parseFloat(oppForm.value) || 0,
        currency: oppForm.currency,
        stage: oppForm.stage,
        contact_id: oppForm.contact_id || null,
        company_id: oppForm.company_id || null,
        assigned_to_id: oppForm.assigned_to_id || null,
        custom_fields: oppForm.custom_fields
      };
      const res = await fetch(`${API_BASE}/opportunities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setOpportunities(prev => [data, ...prev]);
        setShowNewOppModal(false);
      }
    } catch (err) { setError(err.message); }
  };

  // Create Contact
  const handleCreateContact = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(contactForm)
      });
      const data = await res.json();
      if (res.ok) {
        setContacts(prev => [data, ...prev]);
        setShowNewContactModal(false);
      }
    } catch (err) { setError(err.message); }
  };

  // Create Custom Field
  const handleCreateCustomField = async (e) => {
    e.preventDefault();
    try {
      const options = fieldForm.field_type === 'select'
        ? fieldForm.optionsStr.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      const res = await fetch(`${API_BASE}/custom-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ ...fieldForm, options })
      });
      const data = await res.json();
      if (res.ok) {
        setCustomFields(prev => [...prev, data]);
        setShowNewFieldModal(false);
      }
    } catch (err) { setError(err.message); }
  };

  // Invite user
  const handleInviteUser = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(inviteForm)
      });
      const data = await res.json();
      if (res.ok) {
        setSuccessMsg(`Added team member ${data.full_name}`);
        setInviteForm({ full_name: '', email: '', password: 'Password123!', role: 'user', phone: '' });
        fetchTeam();
      }
    } catch (err) { setError(err.message); }
  };

  // Format timestamps in user's local time zone
  const formatLocalTime = (isoStr) => {
    if (!isoStr) return '—';
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

  // Calculate timer remaining seconds
  const getSecondsRemaining = (deadlineStr) => {
    if (!deadlineStr) return null;
    const normalizedIso = (typeof deadlineStr === 'string' && !deadlineStr.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(deadlineStr))
      ? `${deadlineStr}Z`
      : deadlineStr;
    const deadline = new Date(normalizedIso).getTime();
    const diff = Math.max(0, Math.floor((deadline - currentTime) / 1000));
    return diff;
  };

  return (
    <div className="min-h-screen bg-[#BEA884] text-[#4C3D19] flex flex-col font-sans">
      {/* Animations */}
      <style>{`
        @keyframes slideDownIn {
          0% { transform: translateY(-100%); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes slideUpIn {
          0% { transform: translateY(60px); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes fadeIn {
          0% { opacity: 0; }
          100% { opacity: 1; }
        }
        @keyframes popIn {
          0% { transform: translateY(14px) scale(0.96); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes tabIn {
          0% { transform: translateY(12px); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes alertIn {
          0% { transform: translateY(-10px); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes modalIn {
          0% { transform: translateY(24px) scale(0.94); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes rowIn {
          0% { transform: translateX(-12px); opacity: 0; }
          100% { transform: none; opacity: 1; }
        }
        @keyframes floatSlow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-3px); }
        }
        @keyframes urgentGlow {
          0% { box-shadow: inset 0 0 0 0 rgba(159, 18, 57, 0); }
          100% { box-shadow: inset 0 0 22px 2px rgba(159, 18, 57, 0.35); }
        }

        .anim-header { animation: slideDownIn 1s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .anim-card { animation: slideUpIn 1.1s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both; }
        .anim-tab { animation: tabIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .anim-pop { animation: popIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .anim-alert { animation: alertIn 0.4s ease-out both; }
        .anim-fade { animation: fadeIn 0.25s ease-out both; }
        .anim-modal { animation: modalIn 0.4s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .anim-float { animation: floatSlow 3.2s ease-in-out infinite; }
        .anim-urgent::after {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 1rem;
          pointer-events: none;
          animation: urgentGlow 1.1s ease-in-out infinite alternate;
        }

        tbody tr { animation: rowIn 0.45s ease-out both; }
        tbody tr:nth-child(1) { animation-delay: 0.05s; }
        tbody tr:nth-child(2) { animation-delay: 0.1s; }
        tbody tr:nth-child(3) { animation-delay: 0.15s; }
        tbody tr:nth-child(4) { animation-delay: 0.2s; }
        tbody tr:nth-child(5) { animation-delay: 0.25s; }
        tbody tr:nth-child(6) { animation-delay: 0.3s; }
        tbody tr:nth-child(7) { animation-delay: 0.35s; }
        tbody tr:nth-child(8) { animation-delay: 0.4s; }

        button { transition-property: transform, box-shadow, background-color, color, opacity; transition-duration: 0.15s; }
        button:not(:disabled):active { transform: scale(0.96); }
        input, select, textarea { transition: border-color 0.2s ease, box-shadow 0.2s ease; }
        input:focus, select:focus, textarea:focus { box-shadow: 0 0 0 3px rgba(76, 61, 25, 0.25); }

        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { animation: none !important; transition: none !important; }
        }
      `}</style>

      {/* Top Navbar */}
      <header className="border-b border-[#4C3D19]/20 bg-[#BEA884]/80 backdrop-blur sticky top-0 z-40 anim-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#4C3D19] flex items-center justify-center shadow-lg shadow-black/20 anim-float">
              <ShieldCheck className="w-6 h-6 text-[#E5D7C4]" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-[#4C3D19]">
                Lead Protection CRM
              </span>
              <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-[#4C3D19] text-[#E5D7C4] border border-[#4C3D19] font-medium">
                Step 3: Lead Engine & Escalation
              </span>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowPublicFormModal(true)}
                className="px-3 py-1.5 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold flex items-center gap-2 shadow-lg shadow-black/20 transition"
              >
                <Send className="w-3.5 h-3.5" />
                Simulate Web Inbound Lead
              </button>

              <div className="text-right">
                <div className="text-sm font-medium text-[#2A2A2A]">{user.full_name}</div>
                <div className="text-xs text-[#4C3D19] flex items-center gap-1.5 justify-end">
                  <span className="capitalize px-1.5 py-0.2 text-[10px] rounded bg-[#4C3D19]/20 text-[#4C3D19] border border-[#4C3D19]/30">
                    {user.role}
                  </span>
                  <span>•</span>
                  <span className={`capitalize font-semibold ${
                    user.status === 'available' ? 'text-emerald-900' :
                    user.status === 'busy' ? 'text-amber-900' :
                    user.status === 'on_leave' ? 'text-purple-900' : 'text-[#4C3D19]'
                  }`}>
                    {user.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] hover:text-white transition"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        {user && (
          <div className="border-t border-[#4C3D19]/20 px-4 sm:px-6 lg:px-8 bg-[#BEA884]/40">
            <div className="max-w-7xl mx-auto flex items-center gap-2 overflow-x-auto py-2">
              <button
                onClick={() => setActiveTab('lead_engine')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'lead_engine'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Clock className="w-4 h-4 text-amber-600" />
                Lead Protection Inbox ({leads.length})
              </button>
              <button
                onClick={() => setActiveTab('recovery_queue')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'recovery_queue'
                    ? 'bg-rose-900 text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <AlertOctagon className="w-4 h-4 text-rose-600" />
                Recovery Queue ({recoveryQueue.length})
                {recoveryQueue.length > 0 && (
                  <span className="animate-pulse w-2 h-2 rounded-full bg-rose-600" />
                )}
              </button>
              <button
                onClick={() => setActiveTab('pipeline')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'pipeline'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Layers className="w-4 h-4" />
                Pipeline Board ({opportunities.length})
              </button>
              <button
                onClick={() => setActiveTab('contacts')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'contacts'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Users className="w-4 h-4" />
                Contacts & Companies ({contacts.length})
              </button>
              <button
                onClick={() => setActiveTab('custom_fields')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'custom_fields'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Tag className="w-4 h-4" />
                Custom Fields ({customFields.length})
              </button>
              <button
                onClick={() => setActiveTab('workspace')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'workspace'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Settings2 className="w-4 h-4" />
                Team & Availability ({teamMembers.length})
              </button>
              <button
                onClick={() => setActiveTab('integrations')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  activeTab === 'integrations'
                    ? 'bg-[#4C3D19] text-[#E5D7C4] shadow'
                    : 'text-[#4C3D19] hover:text-[#2A2A2A] hover:bg-[#4C3D19]/15'
                }`}
              >
                <Zap className="w-4 h-4 text-amber-600" />
                Integrations & Adapters
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
        {/* Alerts */}
        {error && (
          <div className="mb-4 p-3.5 rounded-xl bg-rose-900/10 border border-rose-900/40 text-rose-900 flex items-center justify-between text-sm anim-alert">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-900" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError('')} className="text-rose-900 hover:text-rose-950 text-xs">Dismiss</button>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3.5 rounded-xl bg-emerald-900/10 border border-emerald-900/40 text-emerald-900 flex items-center justify-between text-sm anim-alert">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-900" />
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg('')} className="text-emerald-900 hover:text-emerald-950 text-xs">Dismiss</button>
          </div>
        )}

        {!token ? (
          /* Authentication Screen */
          <div className="max-w-md mx-auto my-8">
            <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 sm:p-8 shadow-xl anim-card">
              <div className="flex border-b border-black/15 mb-6">
                <button
                  type="button"
                  onClick={() => setIsLoginMode(false)}
                  className={`flex-1 pb-3 text-sm font-semibold transition border-b-2 ${
                    !isLoginMode ? 'border-[#4C3D19] text-[#2A2A2A]' : 'border-transparent text-[#4C3D19]/70 hover:text-[#2A2A2A]'
                  }`}
                >
                  Create Workspace (Signup)
                </button>
                <button
                  type="button"
                  onClick={() => setIsLoginMode(true)}
                  className={`flex-1 pb-3 text-sm font-semibold transition border-b-2 ${
                    isLoginMode ? 'border-[#4C3D19] text-[#2A2A2A]' : 'border-transparent text-[#4C3D19]/70 hover:text-[#2A2A2A]'
                  }`}
                >
                  Sign In
                </button>
              </div>

              {!isLoginMode ? (
                <form onSubmit={handleSignup} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Workspace Name</label>
                    <input
                      type="text"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={signupForm.workspace_name}
                      onChange={(e) => setSignupForm({ ...signupForm, workspace_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Owner Name</label>
                    <input
                      type="text"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={signupForm.full_name}
                      onChange={(e) => setSignupForm({ ...signupForm, full_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Email</label>
                    <input
                      type="email"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={signupForm.email}
                      onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Password (Argon2)</label>
                    <input
                      type="password"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={signupForm.password}
                      onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] rounded-xl text-sm font-semibold transition"
                  >
                    {loading ? 'Creating...' : 'Create Workspace & Owner'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Email</label>
                    <input
                      type="email"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={loginForm.email}
                      onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Password</label>
                    <input
                      type="password"
                      required
                      className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] focus:outline-none focus:border-[#4C3D19]"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] rounded-xl text-sm font-semibold transition"
                  >
                    {loading ? 'Signing In...' : 'Sign In'}
                  </button>
                </form>
              )}
            </div>
          </div>
        ) : (
          /* Logged In Content */
          <div className="space-y-6">
            {/* TAB: LEAD PROTECTION ENGINE (STEP 3 CORE) */}
            {activeTab === 'lead_engine' && (
              <div className="space-y-6 anim-tab">
                {/* Header Banner */}
                <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-[#2A2A2A] flex items-center gap-2">
                      <Flame className="w-6 h-6 text-amber-900" />
                      Lead Protection Inbox
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#4C3D19]/20 text-[#2A2A2A] border border-[#4C3D19]/30">
                        {leads.length} Inbound Leads
                      </span>
                    </h2>
                    <p className="text-xs text-[#4C3D19] mt-1">
                      Every lead has <strong className="text-[#2A2A2A]">exactly one accountable owner</strong>. If ignored, the countdown timer hits zero and auto-escalates to the next rep.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setShowPublicFormModal(true)}
                      className="px-4 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold flex items-center gap-2 shadow-lg shadow-black/20 transition"
                    >
                      <Plus className="w-4 h-4" />
                      Simulate Inbound Lead
                    </button>
                    <button
                      onClick={fetchLeads}
                      className="p-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] transition"
                      title="Refresh"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Leads Table / Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {leads.length === 0 ? (
                    <div className="col-span-full bg-[#6E784B]/60 border border-white/25 rounded-2xl p-12 text-center">
                      <Clock className="w-12 h-12 text-[#4C3D19]/60 mx-auto mb-3" />
                      <h3 className="text-base font-semibold text-[#2A2A2A]">No leads in the inbox yet</h3>
                      <p className="text-xs text-[#4C3D19] max-w-sm mx-auto mt-1 mb-4">
                        Click "Simulate Inbound Lead" to test the public web form and watch the countdown timer start!
                      </p>
                      <button
                        onClick={() => setShowPublicFormModal(true)}
                        className="px-4 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold transition"
                      >
                        Simulate Inbound Lead
                      </button>
                    </div>
                  ) : (
                    leads.map((lead, index) => {
                      const secondsLeft = getSecondsRemaining(lead.acknowledgement_deadline);
                      const isPending = lead.status === 'pending_acknowledgement';
                      const isAck = lead.status === 'acknowledged';
                      const isRecovered = lead.status === 'recovery_queue';

                      return (
                        <div
                          key={lead.id}
                          style={{ animationDelay: `${Math.min(index, 8) * 70}ms` }}
                          className={`bg-[#6E784B] border rounded-2xl p-5 shadow-lg flex flex-col justify-between transition relative overflow-hidden anim-pop ${
                            isPending && secondsLeft !== null && secondsLeft < 10
                              ? 'border-rose-900/60 shadow-rose-900/10 anim-urgent'
                              : isPending
                              ? 'border-amber-900/50 shadow-amber-900/10'
                              : isAck
                              ? 'border-emerald-900/50'
                              : 'border-white/25'
                          }`}
                        >
                          {/* Top Badges */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#E5D7C4]/45 text-[#4C3D19] border border-[#4C3D19]/30">
                                  {lead.source.replace('_', ' ')}
                                </span>
                                <span className="text-[10px] text-[#4C3D19] font-mono">
                                  {formatLocalTime(lead.created_at)}
                                </span>
                              </div>

                              {/* Status Badge */}
                              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                                isAck
                                  ? 'bg-emerald-900/15 text-emerald-900 border-emerald-900/40'
                                  : isPending
                                  ? 'bg-amber-900/15 text-amber-900 border-amber-900/40'
                                  : isRecovered
                                  ? 'bg-rose-900/15 text-rose-900 border-rose-900/40'
                                  : 'bg-[#4C3D19]/20 text-[#2A2A2A] border-[#4C3D19]/40'
                              }`}>
                                {lead.status.replace('_', ' ')}
                              </span>
                            </div>

                            <h3 className="font-bold text-[#2A2A2A] text-sm mb-1">{lead.title}</h3>
                            {lead.notes && (
                              <p className="text-xs text-[#4C3D19] mb-3 bg-[#E5D7C4]/45 p-2.5 rounded-xl border border-[#4C3D19]/20">
                                "{lead.notes}"
                              </p>
                            )}

                            {/* Contact Details */}
                            {lead.contact && (
                              <div className="text-xs text-[#2A2A2A] space-y-1 mb-3">
                                <div className="font-medium text-[#2A2A2A]">{lead.contact.full_name}</div>
                                {lead.contact.phone && (
                                  <div className="text-emerald-900 font-mono text-[11px] flex items-center gap-1.5">
                                    <Phone className="w-3 h-3 text-emerald-900" />
                                    {lead.contact.phone}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Accountability & Escalation Level */}
                            <div className="pt-2 border-t border-[#4C3D19]/20 text-xs flex items-center justify-between">
                              <span className="text-[#4C3D19]">Accountable Owner:</span>
                              <span className="font-semibold text-[#2A2A2A]">
                                {lead.owner ? lead.owner.full_name : <span className="text-rose-900">Unassigned</span>}
                              </span>
                            </div>
                            <div className="text-xs flex items-center justify-between mt-1">
                              <span className="text-[#4C3D19]">Escalation Level:</span>
                              <span className={`font-mono text-xs ${lead.escalation_level > 0 ? 'text-amber-900 font-bold' : 'text-[#2A2A2A]'}`}>
                                Level {lead.escalation_level} {lead.escalation_level === 1 ? '(Backup Rep)' : lead.escalation_level === 2 ? '(Manager)' : ''}
                              </span>
                            </div>
                          </div>

                          {/* Countdown Timer Bar */}
                          {isPending && secondsLeft !== null && (
                            <div className="mt-4 pt-3 border-t border-[#4C3D19]/20">
                              <div className="flex items-center justify-between mb-1.5">
                                <span className="text-[11px] font-semibold text-amber-900 flex items-center gap-1.5">
                                  <Clock className="w-3.5 h-3.5 text-amber-900 animate-spin" />
                                  Acknowledgement Window:
                                </span>
                                <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                                  secondsLeft <= 10 ? 'bg-rose-800 text-white animate-pulse' : 'bg-amber-900/20 text-amber-900'
                                }`}>
                                  ⏱ {secondsLeft}s left
                                </span>
                              </div>
                              <div className="w-full bg-[#E5D7C4]/45 h-1.5 rounded-full overflow-hidden">
                                <div
                                  className={`h-full transition-all duration-1000 ${
                                    secondsLeft <= 10 ? 'bg-rose-800' : 'bg-amber-700'
                                  }`}
                                  style={{ width: `${Math.min(100, (secondsLeft / 20) * 100)}%` }}
                                />
                              </div>
                            </div>
                          )}

                          {isAck && (
                            <div className="mt-4 pt-3 border-t border-[#4C3D19]/20 flex items-center gap-2 text-xs text-emerald-900 font-medium">
                              <CheckCircle2 className="w-4 h-4 text-emerald-900" />
                              Acknowledged in time • Timer Stopped
                            </div>
                          )}

                          {/* Action Buttons */}
                          <div className="mt-4 pt-3 border-t border-[#4C3D19]/20 flex items-center gap-2">
                            {isPending && (
                              <button
                                onClick={() => handleAcknowledge(lead.id)}
                                className="flex-1 py-1.5 px-3 bg-emerald-900 hover:bg-emerald-800 text-[#E5D7C4] text-xs font-semibold rounded-xl transition shadow shadow-black/20 flex items-center justify-center gap-1.5"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Acknowledge Lead
                              </button>
                            )}

                            {isPending && (
                              <button
                                onClick={() => handleForceEscalate(lead.id)}
                                className="py-1.5 px-2.5 bg-rose-900/20 hover:bg-rose-900/30 text-rose-900 text-xs font-semibold rounded-xl border border-rose-900/40 transition flex items-center gap-1"
                                title="Force escalate to backup rep or manager right now for demo testing"
                              >
                                <Flame className="w-3.5 h-3.5 text-rose-900" />
                                Escalate (Demo)
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* TAB: RECOVERY QUEUE */}
            {activeTab === 'recovery_queue' && (
              <div className="space-y-6 anim-tab">
                <div className="bg-[#6E784B] border border-rose-900/40 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-[#2A2A2A] flex items-center gap-2">
                      <AlertOctagon className="w-6 h-6 text-rose-900" />
                      Recovery Queue
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-900/20 text-rose-900 border border-rose-900/40 font-medium">
                        {recoveryQueue.length} Unresolved Leads
                      </span>
                    </h2>
                    <p className="text-xs text-[#4C3D19] mt-1">
                      Leads that reached maximum escalation thresholds without acknowledgement, or arrived when all reps were offline/busy.
                      Any available rep or manager can claim them here.
                    </p>
                  </div>
                  <button
                    onClick={fetchRecoveryQueue}
                    className="p-2 rounded-xl bg-[#4C3D19] text-[#E5D7C4] hover:text-white transition"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>

                <div className="bg-[#6E784B] border border-white/25 rounded-2xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-[#2A2A2A]">
                      <thead className="text-xs uppercase bg-[#4C3D19]/25 text-[#2A2A2A] border-b border-[#4C3D19]/20">
                        <tr>
                          <th className="px-4 py-3">Inquiry / Lead</th>
                          <th className="px-4 py-3">Contact</th>
                          <th className="px-4 py-3">Escalation History</th>
                          <th className="px-4 py-3">Arrival Time</th>
                          <th className="px-4 py-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#4C3D19]/20">
                        {recoveryQueue.length === 0 ? (
                          <tr>
                            <td colSpan="5" className="px-4 py-12 text-center text-[#4C3D19] text-xs">
                              <CheckCircle2 className="w-8 h-8 text-emerald-900 mx-auto mb-2" />
                              Zero dropped leads! Recovery queue is empty.
                            </td>
                          </tr>
                        ) : (
                          recoveryQueue.map((item) => (
                            <tr key={item.id} className="hover:bg-[#4C3D19]/10">
                              <td className="px-4 py-3 font-semibold text-[#2A2A2A]">
                                {item.title}
                                {item.notes && <div className="text-xs text-[#4C3D19] font-normal mt-0.5">{item.notes}</div>}
                              </td>
                              <td className="px-4 py-3 text-xs text-[#2A2A2A]">
                                {item.contact ? (
                                  <div>
                                    <div className="font-medium text-[#2A2A2A]">{item.contact.full_name}</div>
                                    <div className="text-emerald-900 font-mono">{item.contact.phone || item.contact.email}</div>
                                  </div>
                                ) : '—'}
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-900/20 text-rose-900 border border-rose-900/40">
                                  Exhausted Level {item.escalation_level}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-xs text-[#4C3D19]">
                                {formatLocalTime(item.created_at)}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <button
                                  onClick={() => handleClaimLead(item.id)}
                                  className="px-3 py-1.5 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold shadow transition"
                                >
                                  Claim Lead
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: PIPELINE BOARD (From Step 2) */}
            {activeTab === 'pipeline' && (
              <div className="space-y-4 anim-tab">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-[#2A2A2A] flex items-center gap-2">
                      Opportunity Pipeline
                      <span className="text-xs px-2 py-0.5 rounded bg-[#4C3D19]/25 text-[#2A2A2A] font-normal">
                        {opportunities.length} Deals
                      </span>
                    </h2>
                  </div>
                  <button
                    onClick={() => setShowNewOppModal(true)}
                    className="px-3 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold flex items-center gap-2 shadow"
                  >
                    <Plus className="w-4 h-4" />
                    New Opportunity
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 items-start">
                  {PIPELINE_STAGES.map((stageCol, idx) => {
                    const stageOpps = opportunities.filter(o => o.stage === stageCol.id);
                    const totalValue = stageOpps.reduce((sum, o) => sum + (o.value || 0), 0);

                    return (
                      <div
                        key={stageCol.id}
                        style={{ animationDelay: `${idx * 80}ms` }}
                        className="bg-[#6E784B] border border-white/25 rounded-2xl p-3 flex flex-col min-h-[480px] anim-pop"
                      >
                        <div className="pb-3 mb-3 border-b border-[#4C3D19]/20">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold text-[#2A2A2A]">{stageCol.label}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#4C3D19]/25 text-[#2A2A2A] font-semibold">
                              {stageOpps.length}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-[#4C3D19]">
                            ₹{totalValue.toLocaleString('en-IN')}
                          </div>
                        </div>

                        <div className="space-y-3 flex-1 overflow-y-auto max-h-[600px]">
                          {stageOpps.map(opp => (
                            <div key={opp.id} className="bg-[#E5D7C4]/45 border border-[#4C3D19]/25 rounded-xl p-3 shadow anim-pop">
                              <div className="text-xs font-bold text-[#2A2A2A]">{opp.title}</div>
                              <div className="text-xs font-semibold text-emerald-900 mt-1">₹{opp.value.toLocaleString('en-IN')}</div>
                              {opp.contact && <div className="mt-2 text-[11px] text-[#4C3D19]">{opp.contact.full_name}</div>}

                              <div className="mt-3 pt-2 border-t border-[#4C3D19]/20 flex items-center justify-between">
                                {idx > 0 ? (
                                  <button onClick={() => handleStageMove(opp.id, PIPELINE_STAGES[idx - 1].id)} className="p-1 rounded bg-[#4C3D19] text-[#E5D7C4] hover:text-white">
                                    <ArrowLeft className="w-3 h-3" />
                                  </button>
                                ) : <span />}
                                <span className="text-[9px] text-[#4C3D19] uppercase">Move</span>
                                {idx < PIPELINE_STAGES.length - 1 ? (
                                  <button onClick={() => handleStageMove(opp.id, PIPELINE_STAGES[idx + 1].id)} className="p-1 rounded bg-[#4C3D19] text-[#E5D7C4] hover:text-white">
                                    <ArrowRight className="w-3 h-3" />
                                  </button>
                                ) : <span />}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB: CONTACTS (From Step 2) */}
            {activeTab === 'contacts' && (
              <div className="space-y-6 anim-tab">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-[#2A2A2A]">Contacts & Companies ({contacts.length})</h2>
                  <button onClick={() => setShowNewContactModal(true)} className="px-3 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    New Contact
                  </button>
                </div>
                <div className="bg-[#6E784B] border border-white/25 rounded-2xl overflow-hidden">
                  <table className="w-full text-left text-sm text-[#2A2A2A]">
                    <thead className="text-xs uppercase bg-[#4C3D19]/25 text-[#2A2A2A] border-b border-[#4C3D19]/20">
                      <tr>
                        <th className="px-4 py-3">Full Name</th>
                        <th className="px-4 py-3">Phone (WhatsApp)</th>
                        <th className="px-4 py-3">Email</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#4C3D19]/20">
                      {contacts.map(c => (
                        <tr key={c.id}>
                          <td className="px-4 py-3 font-semibold text-[#2A2A2A]">{c.full_name}</td>
                          <td className="px-4 py-3 text-xs font-mono text-emerald-900">{c.phone || '—'}</td>
                          <td className="px-4 py-3 text-xs text-[#4C3D19]">{c.email || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB: CUSTOM FIELDS */}
            {activeTab === 'custom_fields' && (
              <div className="space-y-6 anim-tab">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-[#2A2A2A]">Custom Fields Management</h2>
                  {(user.role === 'owner' || user.role === 'admin') && (
                    <button onClick={() => setShowNewFieldModal(true)} className="px-3 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] text-xs font-semibold flex items-center gap-2">
                      <Plus className="w-4 h-4" /> Add Field
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {['opportunity', 'contact', 'company'].map(entity => (
                    <div key={entity} className="bg-[#6E784B] border border-white/25 rounded-2xl p-5">
                      <h3 className="text-sm font-bold text-[#2A2A2A] uppercase mb-3">{entity} Fields</h3>
                      {customFields.filter(f => f.entity_type === entity).map(f => (
                        <div key={f.id} className="p-2.5 rounded-xl bg-[#E5D7C4]/45 border border-[#4C3D19]/25 mb-2">
                          <div className="text-xs font-semibold text-[#2A2A2A]">{f.label} ({f.field_type})</div>
                          <div className="text-[10px] text-[#4C3D19] font-mono">key: {f.field_key}</div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: WORKSPACE & TEAM AVAILABILITY */}
            {activeTab === 'workspace' && (
              <div className="space-y-8 anim-tab">
                {/* Team Roster with Capacity & Availability Status */}
                <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-base font-bold text-[#2A2A2A] flex items-center gap-2">
                      <Users className="w-5 h-5 text-[#4C3D19]" />
                      Team Availability & Open-Lead Capacity
                    </h2>
                    <button onClick={fetchTeam} className="p-1.5 rounded-lg bg-[#4C3D19] text-[#E5D7C4] hover:text-white">
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-[#2A2A2A]">
                      <thead className="text-xs uppercase bg-[#4C3D19]/25 text-[#2A2A2A] border-b border-[#4C3D19]/20">
                        <tr>
                          <th className="px-4 py-3">Representative</th>
                          <th className="px-4 py-3">Role</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Open Leads</th>
                          <th className="px-4 py-3 text-right">Toggle Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#4C3D19]/20">
                        {teamMembers.map((member) => {
                          const openCount = leads.filter(l => l.owner_id === member.id && l.status === 'pending_acknowledgement').length;
                          const maxCap = workspace?.settings?.max_open_leads_per_rep || 5;

                          return (
                            <tr key={member.id} className="hover:bg-[#4C3D19]/10">
                              <td className="px-4 py-3">
                                <div className="font-medium text-[#2A2A2A]">{member.full_name}</div>
                                <div className="text-xs text-[#4C3D19]">{member.email}</div>
                              </td>
                              <td className="px-4 py-3">
                                <span className="capitalize text-xs font-semibold px-2 py-0.5 rounded bg-[#4C3D19]/25 text-[#2A2A2A]">
                                  {member.role}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                                  member.status === 'available' ? 'bg-emerald-900/15 text-emerald-900 border border-emerald-900/40' :
                                  member.status === 'busy' ? 'bg-amber-900/15 text-amber-900 border border-amber-900/40' :
                                  member.status === 'on_leave' ? 'bg-purple-900/15 text-purple-900 border border-purple-900/40' :
                                  'bg-[#4C3D19]/25 text-[#4C3D19]'
                                }`}>
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    member.status === 'available' ? 'bg-emerald-800' :
                                    member.status === 'busy' ? 'bg-amber-800' :
                                    member.status === 'on_leave' ? 'bg-purple-800' : 'bg-[#4C3D19]/60'
                                  }`} />
                                  {member.status.replace('_', ' ')}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                                  openCount >= maxCap ? 'bg-rose-900/20 text-rose-900' : 'bg-[#4C3D19]/25 text-[#2A2A2A]'
                                }`}>
                                  {openCount} / {maxCap} leads
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right">
                                <select
                                  value={member.status}
                                  onChange={(e) => handleStatusChange(member.id, e.target.value)}
                                  className="text-xs bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-lg px-2 py-1 text-[#2A2A2A]"
                                >
                                  <option value="available">Available</option>
                                  <option value="busy">Busy</option>
                                  <option value="on_leave">On leave (Auto-reassigns!)</option>
                                  <option value="offline">Offline</option>
                                </select>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Configuration: Configurable down to seconds */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6">
                    <h3 className="text-base font-bold text-[#2A2A2A] mb-2 flex items-center gap-2">
                      <Sliders className="w-5 h-5 text-[#4C3D19]" />
                      Lead Engine Timers
                    </h3>
                    <p className="text-xs text-[#4C3D19] mb-4">
                      Set acknowledgement timer down to seconds for live hackathon demonstration.
                    </p>
                    <form onSubmit={handleUpdateSettings} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">
                          Acknowledgement Window (seconds)
                        </label>
                        <input
                          type="number"
                          className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                          value={settingsForm.ackTimeout}
                          onChange={(e) => setSettingsForm({ ...settingsForm, ackTimeout: e.target.value })}
                        />
                        <span className="text-[10px] text-amber-900">Set to 20s for the live demo!</span>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">
                          Max Open Leads Per Rep
                        </label>
                        <input
                          type="number"
                          className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                          value={settingsForm.maxOpenLeads}
                          onChange={(e) => setSettingsForm({ ...settingsForm, maxOpenLeads: e.target.value })}
                        />
                      </div>
                      <button
                        type="submit"
                        className="w-full py-2 bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] rounded-xl text-xs font-semibold transition"
                      >
                        Save Configuration
                      </button>
                    </form>
                  </div>

                  {/* Add Member Form */}
                  <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6">
                    <h3 className="text-base font-bold text-[#2A2A2A] mb-2 flex items-center gap-2">
                      <UserPlus className="w-5 h-5 text-[#4C3D19]" />
                      Invite Rep / Member
                    </h3>
                    <form onSubmit={handleInviteUser} className="space-y-3">
                      <input
                        type="text"
                        placeholder="Full Name (e.g. Rahul Verma)"
                        required
                        className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-xs text-[#2A2A2A]"
                        value={inviteForm.full_name}
                        onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })}
                      />
                      <input
                        type="email"
                        placeholder="Email (e.g. rahul@apexrealty.com)"
                        required
                        className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-xs text-[#2A2A2A]"
                        value={inviteForm.email}
                        onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                      />
                      <input
                        type="password"
                        placeholder="Password"
                        required
                        className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-xs text-[#2A2A2A]"
                        value={inviteForm.password}
                        onChange={(e) => setInviteForm({ ...inviteForm, password: e.target.value })}
                      />
                      <button
                        type="submit"
                        className="w-full py-2 bg-[#4C3D19] hover:bg-[#3a2e12] text-[#E5D7C4] rounded-xl text-xs font-semibold transition"
                      >
                        Add Member
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: PROVIDER ADAPTERS & INTEGRATIONS */}
            {activeTab === 'integrations' && (
              <IntegrationsView
                token={token}
                onError={(msg) => setError(msg)}
                onSuccess={(msg) => setSuccessMsg(msg)}
              />
            )}
          </div>
        )}

        {/* MODAL: SIMULATE PUBLIC INBOUND WEB FORM */}
        {showPublicFormModal && (
          <div className="fixed inset-0 z-50 bg-[#4C3D19]/60 backdrop-blur flex items-center justify-center p-4 anim-fade">
            <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 max-w-lg w-full shadow-2xl anim-modal">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-black/15">
                <h3 className="text-base font-bold text-[#2A2A2A] flex items-center gap-2">
                  <Send className="w-5 h-5 text-[#4C3D19]" />
                  Simulate Public Inbound Web Lead
                </h3>
                <button onClick={() => setShowPublicFormModal(false)} className="text-[#4C3D19] hover:text-[#2A2A2A]">✕</button>
              </div>

              <p className="text-xs text-[#4C3D19] mb-4">
                This triggers the public endpoint <code className="text-emerald-900 font-mono">POST /api/v1/leads/public</code>.
                It automatically routes to the best available rep via round-robin and starts the countdown timer!
              </p>

              <form onSubmit={handlePublicLeadSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Customer Full Name</label>
                  <input
                    type="text"
                    required
                    className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                    value={publicForm.full_name}
                    onChange={(e) => setPublicForm({ ...publicForm, full_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Phone Number (WhatsApp)</label>
                  <input
                    type="text"
                    required
                    className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A] font-mono"
                    value={publicForm.phone}
                    onChange={(e) => setPublicForm({ ...publicForm, phone: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Email</label>
                  <input
                    type="email"
                    className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                    value={publicForm.email}
                    onChange={(e) => setPublicForm({ ...publicForm, email: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase text-[#2A2A2A] mb-1">Inquiry / Note</label>
                  <textarea
                    rows="3"
                    required
                    className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                    value={publicForm.inquiry}
                    onChange={(e) => setPublicForm({ ...publicForm, inquiry: e.target.value })}
                  />
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowPublicFormModal(false)}
                    className="px-4 py-2 rounded-xl bg-[#4C3D19]/25 text-xs font-semibold text-[#2A2A2A]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-[#4C3D19] hover:bg-[#3a2e12] text-xs font-semibold text-[#E5D7C4] shadow"
                  >
                    Send Inbound Lead Now
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: Opportunity */}
        {showNewOppModal && (
          <div className="fixed inset-0 z-50 bg-[#4C3D19]/60 backdrop-blur flex items-center justify-center p-4 anim-fade">
            <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 max-w-lg w-full shadow-2xl anim-modal">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-black/15">
                <h3 className="text-base font-bold text-[#2A2A2A]">New Opportunity</h3>
                <button onClick={() => setShowNewOppModal(false)} className="text-[#4C3D19] hover:text-[#2A2A2A]">✕</button>
              </div>
              <form onSubmit={handleCreateOpportunity} className="space-y-4">
                <input
                  type="text"
                  placeholder="Deal Title"
                  required
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={oppForm.title}
                  onChange={(e) => setOppForm({ ...oppForm, title: e.target.value })}
                />
                <input
                  type="number"
                  placeholder="Value"
                  required
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={oppForm.value}
                  onChange={(e) => setOppForm({ ...oppForm, value: e.target.value })}
                />
                <div className="pt-2 flex justify-end gap-2">
                  <button type="button" onClick={() => setShowNewOppModal(false)} className="px-4 py-2 rounded-xl bg-[#4C3D19]/25 text-xs text-[#2A2A2A]">Cancel</button>
                  <button type="submit" className="px-4 py-2 rounded-xl bg-[#4C3D19] text-xs text-[#E5D7C4]">Save</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: Contact */}
        {showNewContactModal && (
          <div className="fixed inset-0 z-50 bg-[#4C3D19]/60 backdrop-blur flex items-center justify-center p-4 anim-fade">
            <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 max-w-lg w-full shadow-2xl anim-modal">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-black/15">
                <h3 className="text-base font-bold text-[#2A2A2A]">New Contact</h3>
                <button onClick={() => setShowNewContactModal(false)} className="text-[#4C3D19] hover:text-[#2A2A2A]">✕</button>
              </div>
              <form onSubmit={handleCreateContact} className="space-y-4">
                <input
                  type="text"
                  placeholder="Full Name"
                  required
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={contactForm.full_name}
                  onChange={(e) => setContactForm({ ...contactForm, full_name: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Phone"
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={contactForm.phone}
                  onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                />
                <div className="pt-2 flex justify-end gap-2">
                  <button type="button" onClick={() => setShowNewContactModal(false)} className="px-4 py-2 rounded-xl bg-[#4C3D19]/25 text-xs text-[#2A2A2A]">Cancel</button>
                  <button type="submit" className="px-4 py-2 rounded-xl bg-[#4C3D19] text-xs text-[#E5D7C4]">Save</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: Custom Field */}
        {showNewFieldModal && (
          <div className="fixed inset-0 z-50 bg-[#4C3D19]/60 backdrop-blur flex items-center justify-center p-4 anim-fade">
            <div className="bg-[#6E784B] border border-white/25 rounded-2xl p-6 max-w-md w-full shadow-2xl anim-modal">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-black/15">
                <h3 className="text-base font-bold text-[#2A2A2A]">Add Custom Field</h3>
                <button onClick={() => setShowNewFieldModal(false)} className="text-[#4C3D19] hover:text-[#2A2A2A]">✕</button>
              </div>
              <form onSubmit={handleCreateCustomField} className="space-y-4">
                <select
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={fieldForm.entity_type}
                  onChange={(e) => setFieldForm({ ...fieldForm, entity_type: e.target.value })}
                >
                  <option value="opportunity">Opportunity</option>
                  <option value="contact">Contact</option>
                  <option value="company">Company</option>
                </select>
                <input
                  type="text"
                  placeholder="Field Label"
                  required
                  className="w-full bg-[#E5D7C4]/45 border border-[#4C3D19]/35 rounded-xl px-3 py-2 text-sm text-[#2A2A2A]"
                  value={fieldForm.label}
                  onChange={(e) => setFieldForm({ ...fieldForm, label: e.target.value })}
                />
                <div className="pt-2 flex justify-end gap-2">
                  <button type="button" onClick={() => setShowNewFieldModal(false)} className="px-4 py-2 rounded-xl bg-[#4C3D19]/25 text-xs text-[#2A2A2A]">Cancel</button>
                  <button type="submit" className="px-4 py-2 rounded-xl bg-[#4C3D19] text-xs text-[#E5D7C4]">Save</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#4C3D19]/20 py-3 text-center text-xs text-[#4C3D19] bg-[#BEA884]">
        Lead Protection CRM • Hackathon MVP • Step 3: Lead Engine & Escalation Timers
      </footer>
    </div>
  );
}