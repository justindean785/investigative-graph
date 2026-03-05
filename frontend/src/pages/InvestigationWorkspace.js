import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileBox, Users, Network, Clock, Sparkles, Search, Settings, Lightbulb, Brain, Crosshair } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../config/api';
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

  return (
    <div className="h-screen flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <header className="border-b border-white/5 flex items-center justify-between px-4 bg-black/60 backdrop-blur-md flex-shrink-0 z-20" style={{ height: '52px' }}>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-slate-500 hover:text-white h-7 px-2 gap-1.5 text-xs"
            data-testid="return-to-cases-btn"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Cases
          </Button>
          
          <div className="h-4 w-px bg-white/8"></div>
          
          <div className="flex items-center gap-2.5">
            <div className="relative w-6 h-6 flex items-center justify-center flex-shrink-0">
              <div className="absolute inset-0 bg-cyan-500/10 border border-cyan-500/30 rounded-sm" />
              <Crosshair className="w-3.5 h-3.5 text-cyan-400 relative z-10" />
            </div>
            <div>
              <h1 className="text-white font-heading font-bold text-sm leading-tight">{investigation?.name}</h1>
              <p className="text-[9px] text-slate-600 font-mono tracking-wider">{investigation?.case_id}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600" />
            <Input
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              className="pl-7 bg-black/40 border-white/8 h-7 w-40 text-xs"
              placeholder="Search..."
            />
          </div>
          <Button
            variant="ghost"
            className="text-slate-600 hover:text-white h-7 w-7 p-0"
          >
            <Settings className="w-3.5 h-3.5" />
          </Button>
        </div>
      </header>

      {/* Main Content with Tabs */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Tab Navigation */}
        <nav className="w-14 border-r border-white/5 bg-black/40 flex flex-col items-center py-2 gap-0.5 flex-shrink-0">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const TabIcon = tab.icon;
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                data-testid={`tab-${tab.id}`}
                title={`${tab.label} — ${tab.description}`}
                className="relative w-11 h-11 rounded-sm flex flex-col items-center justify-center group"
                style={{
                  background: isActive ? `${tab.color}12` : 'transparent',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Active indicator bar */}
                {isActive && (
                  <div
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
                    style={{ background: tab.color }}
                  />
                )}
                
                <TabIcon
                  className="w-3.5 h-3.5 mb-0.5"
                  style={{ color: isActive ? tab.color : '#475569' }}
                />
                <span
                  className="text-[8px] font-medium leading-none"
                  style={{ color: isActive ? '#e2e8f0' : '#475569' }}
                >
                  {tab.label}
                </span>
                
                {/* Count badge */}
                {tab.count !== null && tab.count > 0 && (
                  <div
                    className="absolute -top-0.5 -right-0.5 h-3.5 min-w-3.5 px-0.5 rounded-sm text-[8px] font-mono font-bold flex items-center justify-center"
                    style={{
                      background: `${tab.color}20`,
                      color: tab.color,
                      border: `1px solid ${tab.color}30`,
                    }}
                  >
                    {tab.count}
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
