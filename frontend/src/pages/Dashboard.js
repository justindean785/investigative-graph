import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Plus, FolderOpen, Clock, Tag, Search, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { API } from '../App';

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
  const [tagInput, setTagInput] = useState('');

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
      toast.success('Investigation created successfully');
      setShowCreateDialog(false);
      setNewInvestigation({ name: '', description: '', tags: [] });
      setTagInput('');
      navigate(`/investigation/${response.data.id}`);
    } catch (error) {
      console.error('Failed to create investigation:', error);
      toast.error('Failed to create investigation');
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !newInvestigation.tags.includes(tagInput.trim())) {
      setNewInvestigation({
        ...newInvestigation,
        tags: [...newInvestigation.tags, tagInput.trim()]
      });
      setTagInput('');
    }
  };

  const removeTag = (tag) => {
    setNewInvestigation({
      ...newInvestigation,
      tags: newInvestigation.tags.filter(t => t !== tag)
    });
  };

  const filteredInvestigations = investigations.filter(inv =>
    inv.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inv.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inv.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-[#0a1628] grid-background">
      {/* Header */}
      <header className="border-b border-[#00d9ff]/20 glass">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#00d9ff] tracking-tight">TRACE ANALYST</h1>
            <p className="text-sm text-[#94a3b8] mt-1 uppercase tracking-widest">OSINT Investigation Platform</p>
          </div>
          
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="create-investigation-btn"
                className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] shadow-[0_0_15px_rgba(0,217,255,0.3)] rounded-sm uppercase font-bold tracking-wider text-xs px-6 py-2 transition-all duration-300"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Investigation
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-xl border-[#00d9ff]/20 text-white">
              <DialogHeader>
                <DialogTitle className="text-2xl text-[#00d9ff]">Create Investigation</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label htmlFor="name" className="text-sm text-[#94a3b8] uppercase tracking-wider">Case Name</Label>
                  <Input
                    id="name"
                    data-testid="investigation-name-input"
                    value={newInvestigation.name}
                    onChange={(e) => setNewInvestigation({ ...newInvestigation, name: e.target.value })}
                    className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 focus:border-[#00d9ff]/60 focus:ring-1 focus:ring-[#00d9ff]/60 text-white"
                    placeholder="Enter investigation name"
                  />
                </div>
                <div>
                  <Label htmlFor="description" className="text-sm text-[#94a3b8] uppercase tracking-wider">Description</Label>
                  <textarea
                    id="description"
                    data-testid="investigation-description-input"
                    value={newInvestigation.description}
                    onChange={(e) => setNewInvestigation({ ...newInvestigation, description: e.target.value })}
                    className="mt-2 w-full bg-[#0a1628] border border-[#00d9ff]/20 focus:border-[#00d9ff]/60 focus:ring-1 focus:ring-[#00d9ff]/60 text-white rounded-md px-4 py-2 min-h-[80px]"
                    placeholder="Brief description of the investigation"
                  />
                </div>
                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Tags</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && addTag()}
                      className="bg-[#0a1628] border-[#00d9ff]/20 focus:border-[#00d9ff]/60 text-white"
                      placeholder="Add tag and press Enter"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {newInvestigation.tags.map(tag => (
                      <Badge
                        key={tag}
                        className="bg-[#00d9ff]/20 text-[#00d9ff] border border-[#00d9ff]/30 cursor-pointer"
                        onClick={() => removeTag(tag)}
                      >
                        {tag} ×
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button
                  data-testid="create-investigation-submit"
                  onClick={createInvestigation}
                  className="w-full bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase tracking-wider"
                >
                  Create Investigation
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#94a3b8]" />
            <Input
              data-testid="search-investigations-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 bg-[#0d1b2a]/50 border-transparent focus:border-[#00d9ff]/40 rounded-full h-12 text-white"
              placeholder="Search investigations by name, description, or tags..."
            />
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="glass border border-[#00d9ff]/20 rounded-lg p-6 hover:border-[#00d9ff]/40 transition-colors duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#94a3b8] uppercase tracking-widest">Total Cases</p>
                <p className="text-3xl font-bold text-white mt-2">{investigations.length}</p>
              </div>
              <FolderOpen className="w-10 h-10 text-[#00d9ff] opacity-50" />
            </div>
          </div>
          
          <div className="glass border border-[#00d9ff]/20 rounded-lg p-6 hover:border-[#00d9ff]/40 transition-colors duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#94a3b8] uppercase tracking-widest">Active</p>
                <p className="text-3xl font-bold text-white mt-2">
                  {investigations.filter(i => i.status === 'active').length}
                </p>
              </div>
              <TrendingUp className="w-10 h-10 text-[#14f195] opacity-50" />
            </div>
          </div>
          
          <div className="glass border border-[#00d9ff]/20 rounded-lg p-6 hover:border-[#00d9ff]/40 transition-colors duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#94a3b8] uppercase tracking-widest">Archived</p>
                <p className="text-3xl font-bold text-white mt-2">
                  {investigations.filter(i => i.status === 'archived').length}
                </p>
              </div>
              <Clock className="w-10 h-10 text-[#94a3b8] opacity-50" />
            </div>
          </div>
        </div>

        {/* Investigations Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
          </div>
        ) : filteredInvestigations.length === 0 ? (
          <div className="glass border border-[#00d9ff]/20 rounded-lg p-12 text-center">
            <FolderOpen className="w-16 h-16 text-[#94a3b8] mx-auto mb-4 opacity-50" />
            <h3 className="text-xl font-bold text-white mb-2">No Investigations Found</h3>
            <p className="text-[#94a3b8] mb-6">Create your first investigation to start tracking entities and relationships</p>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase tracking-wider"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Investigation
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredInvestigations.map(investigation => (
              <div
                key={investigation.id}
                data-testid={`investigation-card-${investigation.id}`}
                onClick={() => navigate(`/investigation/${investigation.id}`)}
                className="glass border border-[#00d9ff]/20 rounded-lg p-6 hover:border-[#00d9ff]/60 hover:shadow-[0_0_15px_rgba(0,217,255,0.15)] transition-all duration-300 cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-white group-hover:text-[#00d9ff] transition-colors">
                      {investigation.name}
                    </h3>
                    <p className="text-xs text-[#94a3b8] font-mono mt-1">{investigation.case_id}</p>
                  </div>
                  <Badge
                    className={`${
                      investigation.status === 'active'
                        ? 'bg-[#14f195]/20 text-[#14f195] border border-[#14f195]/30'
                        : 'bg-[#94a3b8]/20 text-[#94a3b8] border border-[#94a3b8]/30'
                    }`}
                  >
                    {investigation.status}
                  </Badge>
                </div>
                
                {investigation.description && (
                  <p className="text-sm text-[#94a3b8] mb-4 line-clamp-2">{investigation.description}</p>
                )}
                
                {investigation.tags && investigation.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {investigation.tags.slice(0, 3).map(tag => (
                      <Badge
                        key={tag}
                        className="bg-[#00d9ff]/10 text-[#00d9ff] border border-[#00d9ff]/20 text-xs"
                      >
                        <Tag className="w-3 h-3 mr-1" />
                        {tag}
                      </Badge>
                    ))}
                    {investigation.tags.length > 3 && (
                      <Badge className="bg-[#94a3b8]/10 text-[#94a3b8] text-xs">
                        +{investigation.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
                
                <div className="flex items-center justify-between pt-4 border-t border-[#00d9ff]/10">
                  <div className="flex items-center text-xs text-[#94a3b8]">
                    <Clock className="w-3 h-3 mr-1" />
                    {formatDate(investigation.created_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
