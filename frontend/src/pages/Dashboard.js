import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, FolderOpen, Clock, Settings, Activity, Shield, Network, ChevronRight, Crosshair } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import axios, { API } from '../config/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState({
    name: '',
    description: '',
    tags: []
  });

  useEffect(() => {
    fetchInvestigations();
  }, []);

  const fetchInvestigations = async () => {
    try {
      const response = await axios.get(`${API}/investigations`);
      setInvestigations(response.data);
    } catch (error) {
      console.error('Failed to fetch investigations:', error);
      toast.error('Failed to load investigations');
    } finally {
      setLoading(false);
    }
  };

  const createInvestigation = async () => {
    if (!newInvestigation.name.trim()) {
      toast.error('Investigation name is required');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations`, newInvestigation);
      toast.success('Investigation created');
      setShowCreateDialog(false);
      setNewInvestigation({ name: '', description: '', tags: [] });
      navigate(`/investigation/${response.data.id}`);
    } catch (error) {
      console.error('Failed to create investigation:', error);
      toast.error('Failed to create investigation');
    }
  };

  const filteredInvestigations = investigations.filter(inv =>
    inv.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (inv.description || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const activeCount = investigations.filter(i => i.status === 'active').length;

  return (
    <div className="h-screen flex flex-col bg-[#050505]">
      {/* Header */}
      <header className="h-13 border-b border-white/5 flex items-center justify-between px-6 bg-black/60 backdrop-blur-md flex-shrink-0" style={{ height: '52px' }}>
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="relative w-8 h-8 flex items-center justify-center">
            <div className="absolute inset-0 bg-cyan-500/10 border border-cyan-500/30 rounded-sm" />
            <Crosshair className="w-4 h-4 text-cyan-400 relative z-10" />
          </div>
          <div>
            <span className="font-heading font-bold text-white text-sm tracking-widest uppercase">Trace Analyst</span>
            <div className="flex items-center gap-1 mt-px">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">OSINT Platform</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-4 mr-2">
            <div className="text-center">
              <p className="text-xs font-mono text-cyan-400 font-bold">{investigations.length}</p>
              <p className="text-[9px] text-slate-600 uppercase tracking-wider">Total</p>
            </div>
            <div className="w-px h-6 bg-white/5" />
            <div className="text-center">
              <p className="text-xs font-mono text-emerald-400 font-bold">{activeCount}</p>
              <p className="text-[9px] text-slate-600 uppercase tracking-wider">Active</p>
            </div>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium px-4 h-8 rounded-sm"
            style={{ boxShadow: '0 0 12px rgba(6,182,212,0.25)' }}
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            New Investigation
          </Button>
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 overflow-hidden flex">
        {/* Sidebar */}
        <aside className="w-64 border-r border-white/5 bg-black/40 flex flex-col flex-shrink-0">
          <div className="p-3 border-b border-white/5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-black/60 border-white/8 h-8 text-xs"
                placeholder="Search cases..."
              />
            </div>
          </div>

          <div className="p-3 border-b border-white/5">
            <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-2">Case Navigator</div>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="w-full bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 text-xs h-8 rounded-sm border border-cyan-500/20 hover:border-cyan-500/40"
            >
              <Plus className="w-3 h-3 mr-1.5" />
              New Case
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {filteredInvestigations.map(inv => (
              <div
                key={inv.id}
                onClick={() => navigate(`/investigation/${inv.id}`)}
                className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-sm cursor-pointer group"
              >
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${inv.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                <span className="text-xs text-slate-400 group-hover:text-slate-200 truncate flex-1">{inv.name}</span>
                <ChevronRight className="w-3 h-3 text-slate-700 group-hover:text-slate-400 flex-shrink-0 opacity-0 group-hover:opacity-100" />
              </div>
            ))}
          </div>

          <div className="p-3 border-t border-white/5">
            <Button
              variant="ghost"
              className="w-full justify-start text-slate-500 hover:text-slate-300 text-xs h-8 gap-2"
            >
              <Settings className="w-3.5 h-3.5" />
              Settings
            </Button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="loading-spinner w-10 h-10"></div>
            </div>
          ) : filteredInvestigations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="relative">
                {/* Glow ring */}
                <div className="absolute inset-0 rounded-sm bg-cyan-500/5 border border-cyan-500/10 blur-sm scale-110" />
                <div className="glass rounded-sm p-12 max-w-md text-center relative">
                  <div className="w-16 h-16 mx-auto mb-5 relative">
                    <div className="absolute inset-0 bg-cyan-500/10 border border-cyan-500/20 rounded-sm" />
                    <FolderOpen className="w-8 h-8 text-cyan-500/60 absolute inset-1/2 -translate-x-1/2 -translate-y-1/2" />
                  </div>
                  <h2 className="text-xl font-heading font-bold text-white mb-2">No Investigations</h2>
                  <p className="text-sm text-slate-400 mb-6 leading-relaxed">
                    Create your first investigation to start tracking entities and relationships
                  </p>
                  <Button
                    onClick={() => setShowCreateDialog(true)}
                    className="bg-cyan-600 hover:bg-cyan-500 text-white rounded-sm"
                    style={{ boxShadow: '0 0 16px rgba(6,182,212,0.3)' }}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Investigation
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6 max-w-6xl">
              {/* Page header */}
              <div className="flex items-end justify-between">
                <div>
                  <h1 className="text-2xl font-heading font-bold text-white tracking-tight">
                    Intelligence Cases
                  </h1>
                  <p className="text-xs text-slate-500 mt-1 font-mono">
                    {filteredInvestigations.length} case{filteredInvestigations.length !== 1 ? 's' : ''} 
                    {searchQuery ? ` matching "${searchQuery}"` : ''}
                  </p>
                </div>
                {/* Stats bar */}
                <div className="flex items-center gap-6 mb-1">
                  <div className="flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-xs text-slate-400"><span className="text-emerald-400 font-mono font-semibold">{activeCount}</span> active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Shield className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-xs text-slate-400"><span className="text-slate-300 font-mono font-semibold">{investigations.length - activeCount}</span> archived</span>
                  </div>
                </div>
              </div>

              {/* Cases grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredInvestigations.map(inv => (
                  <div
                    key={inv.id}
                    onClick={() => navigate(`/investigation/${inv.id}`)}
                    className="case-card group relative bg-black/50 border border-white/[0.08] rounded-sm p-5 cursor-pointer overflow-hidden"
                  >
                    {/* Accent line top */}
                    <div
                      className="absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100"
                      style={{
                        background: 'linear-gradient(90deg, transparent, rgba(6,182,212,0.6), transparent)',
                        transition: 'opacity 0.2s',
                      }}
                    />

                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        {/* Case icon */}
                        <div className="w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0 mt-0.5"
                          style={{ background: inv.status === 'active' ? 'rgba(16,185,129,0.1)' : 'rgba(100,116,139,0.1)', border: `1px solid ${inv.status === 'active' ? 'rgba(16,185,129,0.25)' : 'rgba(100,116,139,0.2)'}` }}
                        >
                          <Network className="w-4 h-4" style={{ color: inv.status === 'active' ? '#10b981' : '#64748b' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-heading font-semibold text-white group-hover:text-cyan-300 truncate"
                            style={{ transition: 'color 0.2s' }}>
                            {inv.name}
                          </h3>
                          <p className="text-[10px] font-mono text-slate-600 mt-0.5">{inv.case_id}</p>
                        </div>
                      </div>
                      <div className={`flex-shrink-0 ml-2 text-[10px] px-2 py-0.5 rounded-sm font-mono uppercase tracking-wider ${
                        inv.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-slate-500/10 text-slate-500 border border-slate-500/20'
                      }`}>
                        {inv.status}
                      </div>
                    </div>

                    {inv.description && (
                      <p className="text-xs text-slate-500 mb-4 line-clamp-2 leading-relaxed">{inv.description}</p>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-mono">
                        <Clock className="w-3 h-3" />
                        {formatDate(inv.created_at)}
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-cyan-500/50 group-hover:text-cyan-400 opacity-0 group-hover:opacity-100"
                        style={{ transition: 'opacity 0.2s, color 0.2s' }}>
                        <span>Open</span>
                        <ChevronRight className="w-3 h-3" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="glass-strong border-white/10 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-heading flex items-center gap-2">
              <div className="w-6 h-6 rounded-sm bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
                <Plus className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              Create Investigation
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-2 block">Case Name</Label>
              <Input
                value={newInvestigation.name}
                onChange={(e) => setNewInvestigation({ ...newInvestigation, name: e.target.value })}
                className="bg-black/50 border-white/10 focus:border-cyan-500/50 text-white"
                placeholder="Enter investigation name"
                onKeyDown={(e) => e.key === 'Enter' && createInvestigation()}
              />
            </div>
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-2 block">Description</Label>
              <textarea
                value={newInvestigation.description}
                onChange={(e) => setNewInvestigation({ ...newInvestigation, description: e.target.value })}
                className="w-full bg-black/50 border border-white/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 rounded-sm px-3 py-2 text-sm text-white min-h-[80px] placeholder:text-slate-600"
                placeholder="Brief description"
              />
            </div>
            <Button
              onClick={createInvestigation}
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white rounded-sm h-10 font-medium"
              style={{ boxShadow: '0 0 14px rgba(6,182,212,0.25)' }}
            >
              Create Investigation
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Dashboard;
