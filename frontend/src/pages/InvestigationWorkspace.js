import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileBox, Users, Network, Clock, Sparkles, Search, Settings, Lightbulb, Brain, Download, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API, API_KEY, BACKEND_URL } from '../config/api';
import useInvestigationStore from '../store/investigationStore';
import EvidenceWorkspace from '../components/workspace/EvidenceWorkspace';
import EntitiesWorkspace from '../components/workspace/EntitiesWorkspace';
import GraphView from '../components/workspace/GraphView';
import TimelineWorkspace from '../components/workspace/TimelineWorkspace';
import AISuggestionsWorkspace from '../components/workspace/AISuggestionsWorkspace';
import LeadsWorkspace from '../components/workspace/LeadsWorkspace';
import AIChatWorkspace from '../components/workspace/AIChatWorkspace';

const InvestigationWorkspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('evidence'); // Evidence-first workflow
  const [globalSearch, setGlobalSearch] = useState('');
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  
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
    clearInvestigation,
  } = useInvestigationStore();

  useEffect(() => {
    loadInvestigation();
    return () => clearInvestigation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        title: e.content?.slice(0, 50) || e.evidence_type,
        sourceUrl: e.source_url || '',
        content: e.content || '',
        notes: e.notes || '',
        tags: e.tags || [],
        verificationStatus: e.verification_status || 'unverified',
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
        <div className="text-center">
          <div className="loading-spinner w-12 h-12 mx-auto mb-4"></div>
          <p className="text-sm text-slate-400">Loading investigation...</p>
        </div>
      </div>
    );
  }

  // Tab configuration with workflow order
  const tabs = [
    { 
      id: 'evidence', 
      label: 'Evidence', 
      icon: FileBox,
      count: evidence.length,
      color: '#fbbf24',
      description: 'Collect and document findings'
    },
    { 
      id: 'entities', 
      label: 'Entities', 
      icon: Users,
      count: entities.length,
      color: '#14f195',
      description: 'Identify subjects and objects'
    },
    { 
      id: 'graph', 
      label: 'Graph', 
      icon: Network,
      count: relationships.length,
      color: '#06b6d4',
      description: 'Visualize connections'
    },
    { 
      id: 'leads', 
      label: 'Leads', 
      icon: Lightbulb,
      count: null,
      color: '#f97316',
      description: 'Auto-generated hypotheses'
    },
    { 
      id: 'timeline', 
      label: 'Timeline', 
      icon: Clock,
      count: timeline.length,
      color: '#94a3b8',
      description: 'Track investigation history'
    },
    { 
      id: 'chat', 
      label: 'AI Chat', 
      icon: Brain,
      count: null,
      color: '#14f195',
      description: 'Interactive AI analyst'
    },
    { 
      id: 'ai', 
      label: 'AI Gen', 
      icon: Sparkles,
      count: null,
      color: '#7c3aed',
      description: 'AI-powered suggestions'
    },
  ];

  const navigateToTab = (tabId) => setActiveTab(tabId);

  /**
   * Trigger a file download by navigating to an export endpoint.
   * The browser will handle the Content-Disposition header and save the file.
   */
  const handleExport = (format) => {
    const url = `${BACKEND_URL}/api/investigations/${id}/export/${format}`;
    // Fetch with auth header and trigger browser download via a blob URL
    fetch(url, { headers: { 'x-api-key': API_KEY } })
      .then((res) => {
        if (!res.ok) throw new Error('Export failed');
        return res.blob();
      })
      .then((blob) => {
        const ext = { json: 'json', csv: 'zip', markdown: 'md' }[format] || format;
        const objUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objUrl;
        a.download = `${investigation?.case_id || id}_export.${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(objUrl);
        toast.success(`${format.toUpperCase()} export downloaded`);
      })
      .catch(() => toast.error('Export failed'))
      .finally(() => setExportMenuOpen(false));
  };

  return (
    <div className="h-screen flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <header className="h-14 border-b border-white/5 flex items-center justify-between px-4 bg-black/50 backdrop-blur-sm flex-shrink-0 z-20">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white h-8 px-2 gap-1.5 text-xs"
            data-testid="return-to-cases-btn"
          >
            <ArrowLeft className="w-4 h-4" />
            Cases
          </Button>
          
          <div className="h-5 w-px bg-white/10"></div>
          
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-primary/20 border border-primary/40 rounded-sm flex items-center justify-center text-primary text-sm font-bold">
              T
            </div>
            <div>
              <h1 className="text-white font-heading font-bold text-sm leading-tight">{investigation?.name}</h1>
              <p className="text-[10px] text-slate-500 font-mono">{investigation?.case_id}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <Input
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              className="pl-8 bg-black/30 border-white/10 h-8 w-48 text-xs"
              placeholder="Search..."
            />
          </div>
          {/* Export dropdown */}
          <div className="relative">
            <Button
              variant="ghost"
              onClick={() => setExportMenuOpen((v) => !v)}
              className="text-slate-400 hover:text-white h-8 px-2 gap-1 text-xs"
              title="Export investigation"
              data-testid="export-btn"
            >
              <Download className="w-3.5 h-3.5" />
              Export
              <ChevronDown className="w-3 h-3" />
            </Button>
            {exportMenuOpen && (
              <div className="absolute right-0 top-full mt-1 bg-[#111] border border-white/10 rounded-sm shadow-xl z-50 min-w-[140px]">
                {[
                  { fmt: 'json', label: 'JSON (full data)' },
                  { fmt: 'csv', label: 'CSV (ZIP)' },
                  { fmt: 'markdown', label: 'Markdown report' },
                ].map(({ fmt, label }) => (
                  <button
                    key={fmt}
                    onClick={() => handleExport(fmt)}
                    className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            className="text-slate-400 hover:text-white h-8 w-8 p-0"
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Main Content with Tabs */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Tab Navigation */}
        <nav className="w-16 border-r border-white/5 bg-black/30 flex flex-col items-center py-3 gap-1 flex-shrink-0">
          {tabs.map((tab, index) => {
            const isActive = activeTab === tab.id;
            const TabIcon = tab.icon;
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                data-testid={`tab-${tab.id}`}
                className={`relative w-12 h-12 rounded-sm flex flex-col items-center justify-center transition-all group ${
                  isActive 
                    ? 'bg-white/10' 
                    : 'hover:bg-white/5'
                }`}
                title={tab.description}
              >
                {/* Active indicator */}
                {isActive && (
                  <div 
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-r"
                    style={{ backgroundColor: tab.color }}
                  />
                )}
                
                <TabIcon 
                  className="w-4 h-4 mb-0.5" 
                  style={{ color: isActive ? tab.color : '#64748b' }}
                />
                <span className={`text-[9px] font-medium ${isActive ? 'text-white' : 'text-slate-500'}`}>
                  {tab.label}
                </span>
                
                {/* Count badge */}
                {tab.count !== null && tab.count > 0 && (
                  <Badge 
                    className="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 text-[9px] border-0 flex items-center justify-center"
                    style={{ 
                      backgroundColor: `${tab.color}20`,
                      color: tab.color 
                    }}
                  >
                    {tab.count}
                  </Badge>
                )}

                {/* Workflow indicator (arrow) */}
                {index < tabs.length - 1 && (
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-slate-700 text-[8px]">
                    ↓
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Content Area */}
        <main className="flex-1 overflow-hidden bg-[#0a0a0a]">
          {activeTab === 'evidence' && (
            <EvidenceWorkspace 
              investigationId={id} 
              onNavigateToEntities={() => navigateToTab('entities')}
            />
          )}
          {activeTab === 'entities' && (
            <EntitiesWorkspace 
              investigationId={id}
              onNavigateToGraph={() => navigateToTab('graph')}
              onNavigateToEvidence={() => navigateToTab('evidence')}
            />
          )}
          {activeTab === 'graph' && (
            <GraphView 
              investigationId={id}
              onNavigateToEvidence={() => navigateToTab('evidence')}
              onNavigateToEntities={() => navigateToTab('entities')}
            />
          )}
          {activeTab === 'leads' && (
            <LeadsWorkspace 
              investigationId={id}
              onNavigateToEvidence={() => navigateToTab('evidence')}
              onNavigateToEntities={() => navigateToTab('entities')}
            />
          )}
          {activeTab === 'timeline' && (
            <TimelineWorkspace 
              onNavigateToEvidence={() => navigateToTab('evidence')}
            />
          )}
          {activeTab === 'chat' && (
            <AIChatWorkspace 
              investigationId={id}
              onNavigateToEvidence={() => navigateToTab('evidence')}
            />
          )}
          {activeTab === 'ai' && (
            <AISuggestionsWorkspace 
              investigationId={id}
              onNavigateToEvidence={() => navigateToTab('evidence')}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default InvestigationWorkspace;
