import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Network, MapPin, Clock, Table, Settings, Plus, Search, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { API, API_KEY } from '../App';
import useInvestigationStore from '../store/investigationStore';
import GraphView from '../components/workspace/GraphView';
import EntitiesPanel from '../components/workspace/EntitiesPanel';

axios.defaults.headers.common['x-api-key'] = API_KEY;

const InvestigationWorkspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('graph');
  const [globalSearch, setGlobalSearch] = useState('');
  
  const {
    investigation,
    entities,
    relationships,
    timeline,
    evidence,
    setInvestigation,
    setEntities,
    setRelationships,
    setTimeline,
    setEvidence,
  } = useInvestigationStore();

  useEffect(() => {
    loadInvestigation();
  }, [id]);

  const loadInvestigation = async () => {
    try {
      const [invRes, entRes, relRes, timeRes, evRes] = await Promise.all([
        axios.get(`${API}/investigations/${id}`),
        axios.get(`${API}/investigations/${id}/entities`),
        axios.get(`${API}/investigations/${id}/relationships`),
        axios.get(`${API}/investigations/${id}/timeline`),
        axios.get(`${API}/investigations/${id}/evidence`),
      ]);

      setInvestigation(invRes.data);
      
      // Convert entities to store format
      const mappedEntities = entRes.data.map(e => ({
        id: e.id,
        kind: e.entity_type,
        value: e.value,
        label: e.label || e.value,
        notes: e.notes || '',
        tags: [],
        sources: e.sources || [],
        confidence: e.confidence || 0.5,
        risk: (e.risk_score || 0) * 100,
        createdAt: e.created_at,
        updatedAt: e.updated_at || e.created_at,
      }));

      // Convert relationships to store format
      const mappedRelationships = relRes.data.map(r => ({
        id: r.id,
        fromId: r.source_entity_id,
        toId: r.target_entity_id,
        relType: r.relationship_type,
        label: r.label || r.relationship_type,
        confidence: r.confidence || 0.5,
        sources: [],
        createdAt: r.created_at,
      }));

      // Convert timeline to store format
      const mappedTimeline = timeRes.data.map(t => ({
        id: t.id,
        ts: t.timestamp,
        type: t.event_type,
        summary: t.description,
        refs: {
          entityIds: t.entity_id ? [t.entity_id] : [],
          evidenceIds: [],
          edgeIds: [],
        },
        meta: t.metadata || {},
      }));

      // Convert evidence to store format
      const mappedEvidence = evRes.data.map(e => ({
        id: e.id,
        type: e.evidence_type,
        title: e.evidence_type,
        sourceUrl: e.source_url || '',
        content: e.content || '',
        notes: e.notes || '',
        hash: '',
        linked: {
          entityIds: e.entity_id ? [e.entity_id] : [],
          edgeIds: [],
        },
        collectedAt: e.collected_at,
      }));

      setEntities(mappedEntities);
      setRelationships(mappedRelationships);
      setTimeline(mappedTimeline);
      setEvidence(mappedEvidence);
    } catch (error) {
      console.error('Failed to load investigation:', error);
      toast.error('Failed to load investigation');
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen bg-[#050505] flex items-center justify-center">
        <div className="loading-spinner w-12 h-12"></div>
      </div>
    );
  }

  const tabs = [
    { id: 'graph', label: 'Graph', icon: Network },
    { id: 'map', label: 'Map', icon: MapPin },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'table', label: 'Table', icon: Table },
  ];

  return (
    <div className="h-screen flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <header className="h-12 border-b border-white/5 flex items-center justify-between px-4 bg-black/50 backdrop-blur-sm flex-shrink-0 z-20">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white h-8 px-2 gap-1 text-xs"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Cases
          </Button>
          
          <div className="h-4 w-px bg-white/5"></div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 font-heading font-bold text-base">
              <div className="w-6 h-6 bg-primary/20 border border-primary/50 rounded flex items-center justify-center text-primary text-sm">T</div>
              <span className="text-white">TRACE ANALYST</span>
            </div>
            <span className="text-slate-500 text-sm">›</span>
            <span className="text-white text-sm">{investigation?.name}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">{investigation?.case_id}</span>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-white/5 bg-black/50 flex flex-col z-10 flex-shrink-0">
          <div className="p-3 border-b border-white/5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                className="pl-9 bg-[#0a0a0a] border-white/10 h-9 text-sm"
                placeholder="Global search..."
              />
            </div>
          </div>

          <div className="p-2 border-b border-white/5 flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">CASE NAVIGATOR</span>
            <Button className="bg-primary/10 text-primary hover:bg-primary/20 px-2 py-1 h-6 rounded-sm text-xs">
              <Plus className="w-3 h-3 mr-1" />
              New
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            <div className="space-y-1">
              <div className="text-slate-400 hover:text-white px-3 py-2 hover:bg-white/5 rounded-sm cursor-pointer text-sm flex items-center gap-2">
                <Network className="w-4 h-4" />
                {investigation?.name}
              </div>
            </div>
          </div>

          <div className="p-3 border-t border-white/5">
            <Button
              variant="ghost"
              className="w-full justify-center text-slate-400 hover:text-white text-xs h-9"
            >
              <Settings className="w-4 h-4 mr-2" />
              Workspace Settings
            </Button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 relative flex flex-col min-w-0 overflow-hidden">
          {/* Tab Bar */}
          <div className="h-12 border-b border-white/5 bg-black/50 backdrop-blur-sm z-10 flex items-center px-4 gap-6 flex-shrink-0">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 h-full px-1 text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'text-primary border-b-2 border-primary font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
            
            <div className="flex-1"></div>
            
            {activeTab === 'graph' && (
              <div className="flex items-center gap-1 bg-[#0a0a0a] rounded-sm border border-white/10 p-1">
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-slate-400 hover:text-white">
                  <Plus className="w-4 h-4" />
                </Button>
                <span className="text-xs text-slate-400 px-2 min-w-[3ch] text-center font-mono">100%</span>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-slate-400 hover:text-white">
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <div className="w-px h-4 bg-white/10 mx-1"></div>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-slate-400 hover:text-white">
                  <Maximize2 className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Content Area */}
          <div className="flex-1 relative overflow-hidden bg-[#0a0a0a]">
            {activeTab === 'graph' && <GraphView investigationId={id} />}
            {activeTab === 'timeline' && (
              <div className="h-full flex items-center justify-center">
                <p className="text-slate-500">Timeline view coming soon</p>
              </div>
            )}
            {activeTab === 'map' && (
              <div className="h-full flex items-center justify-center">
                <p className="text-slate-500">Map view coming soon</p>
              </div>
            )}
            {activeTab === 'table' && (
              <div className="h-full flex items-center justify-center">
                <p className="text-slate-500">Table view coming soon</p>
              </div>
            )}
          </div>
        </main>

        {/* Right Sidebar - Entities Panel */}
        <EntitiesPanel investigationId={id} />
      </div>
    </div>
  );
};

export default InvestigationWorkspace;
