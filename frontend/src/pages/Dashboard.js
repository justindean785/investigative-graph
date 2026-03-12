import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, FolderOpen, Clock, Settings } from 'lucide-react';
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

  const filteredInvestigations = useMemo(() => investigations.filter(inv =>
    inv.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inv.description.toLowerCase().includes(searchQuery.toLowerCase())
  ), [investigations, searchQuery]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="h-screen flex flex-col bg-[#050505]">
      {/* Header */}
      <header className="h-12 border-b border-white/5 flex items-center justify-between px-4 bg-black/50 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 font-heading font-bold text-base">
            <div className="w-6 h-6 bg-primary/20 border border-primary/50 rounded flex items-center justify-center text-primary text-sm">T</div>
            <span className="text-white">TRACE ANALYST</span>
          </div>
        </div>
        <Button
          onClick={() => setShowCreateDialog(true)}
          className="bg-primary hover:bg-primary/90 text-white text-xs font-medium px-4 h-8 rounded-sm shadow-glow"
        >
          <Plus className="w-4 h-4 mr-1" />
          New Investigation
        </Button>
      </header>

      {/* Main */}
      <div className="flex-1 overflow-hidden flex">
        {/* Sidebar */}
        <aside className="w-64 border-r border-white/5 bg-black/50 flex flex-col flex-shrink-0">
          <div className="p-3 border-b border-white/5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-[#0a0a0a] border-white/10 h-9 text-sm"
                placeholder="Search investigations..."
              />
            </div>
          </div>

          <div className="p-3 border-b border-white/5">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">CASE NAVIGATOR</div>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="w-full bg-primary/10 text-primary hover:bg-primary/20 text-xs h-8 rounded-sm"
            >
              <Plus className="w-3 h-3 mr-1" />
              New Case
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {filteredInvestigations.map(inv => (
              <div
                key={inv.id}
                onClick={() => navigate(`/investigation/${inv.id}`)}
                className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-sm cursor-pointer text-slate-400 hover:text-white transition-colors group"
              >
                <FolderOpen className="w-4 h-4" />
                <span className="text-sm truncate flex-1">{inv.name}</span>
              </div>
            ))}
          </div>

          <div className="p-3 border-t border-white/5">
            <Button
              variant="ghost"
              className="w-full justify-center text-slate-400 hover:text-white text-xs h-9"
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="loading-spinner w-12 h-12"></div>
            </div>
          ) : filteredInvestigations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="glass rounded-sm p-12 max-w-md text-center">
                <FolderOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h2 className="text-xl font-heading font-bold text-white mb-2">No Investigations</h2>
                <p className="text-sm text-slate-400 mb-6">Create your first investigation to start tracking entities and relationships</p>
                <Button
                  onClick={() => setShowCreateDialog(true)}
                  className="bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Investigation
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-heading font-bold text-white mb-2">Investigations</h1>
                <p className="text-sm text-slate-400">Manage and track your intelligence cases</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredInvestigations.map(inv => (
                  <div
                    key={inv.id}
                    onClick={() => navigate(`/investigation/${inv.id}`)}
                    className="glass rounded-sm p-5 hover:border-primary/30 cursor-pointer transition-all group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="text-base font-heading font-semibold text-white group-hover:text-primary transition-colors mb-1">
                          {inv.name}
                        </h3>
                        <p className="text-xs font-mono text-slate-500">{inv.case_id}</p>
                      </div>
                      <div className={`text-xs px-2 py-1 rounded-sm ${
                        inv.status === 'active' 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                      }`}>
                        {inv.status}
                      </div>
                    </div>

                    {inv.description && (
                      <p className="text-sm text-slate-400 mb-4 line-clamp-2">{inv.description}</p>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <div className="flex items-center gap-1 text-xs text-slate-500">
                        <Clock className="w-3 h-3" />
                        {formatDate(inv.created_at)}
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
            <DialogTitle className="text-xl font-heading">Create Investigation</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-2 block">Case Name</Label>
              <Input
                value={newInvestigation.name}
                onChange={(e) => setNewInvestigation({ ...newInvestigation, name: e.target.value })}
                className="bg-black/50 border-white/10 focus:border-primary/50 text-white"
                placeholder="Enter investigation name"
                onKeyPress={(e) => e.key === 'Enter' && createInvestigation()}
              />
            </div>
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-2 block">Description</Label>
              <textarea
                value={newInvestigation.description}
                onChange={(e) => setNewInvestigation({ ...newInvestigation, description: e.target.value })}
                className="w-full bg-black/50 border border-white/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/20 rounded-sm px-3 py-2 text-sm text-white min-h-[80px]"
                placeholder="Brief description"
              />
            </div>
            <Button
              onClick={createInvestigation}
              className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow h-10 font-medium"
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
