import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Network, Users, FileText, Shield, Settings, Save, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';
import UniversalInput from '../investigation/UniversalInput';
import LiveFeed from '../investigation/LiveFeed';
import GraphView from '../workspace/GraphView';
import EntitiesWorkspace from '../workspace/EntitiesWorkspace';
import EvidenceWorkspace from '../workspace/EvidenceWorkspace';
import ReportView from '../workspace/ReportView';

const UnifiedInvestigation = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rightPanel, setRightPanel] = useState('feed');
  const [showCasePanel, setShowCasePanel] = useState(false);
  const [caseNotes, setCaseNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const lastStreamRefreshRef = useRef(0);

  const {
    investigation,
    entities,
    relationships,
    evidence,
    setInvestigation,
    setEntities,
    setRelationships,
    setEvidence,
    clearInvestigation,
  } = useInvestigationStore();

  const loadInvestigation = useCallback(async () => {
    try {
      const [invRes, entRes, relRes, evRes] = await Promise.all([
        axios.get(`${API}/investigations/${id}`),
        axios.get(`${API}/investigations/${id}/entities`),
        axios.get(`${API}/investigations/${id}/relationships`),
        axios.get(`${API}/investigations/${id}/evidence`),
      ]);

      setInvestigation(invRes.data);
      setCaseNotes(invRes.data.notes || '');
      
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
          entityIds: e.entity_id ? [e.entity_id] : e.entity_ids || [],
          edgeIds: [],
        },
        collectedAt: e.collected_at,
      }));

      setEntities(mappedEntities);
      setRelationships(mappedRelationships);
      setEvidence(mappedEvidence);
    } catch (error) {
      console.error('Failed to load investigation:', error);
      if (loading) {
        toast.error('Failed to load investigation');
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, navigate]);

  const refreshFromStream = useCallback(() => {
    const now = Date.now();
    if (now - lastStreamRefreshRef.current < 1500) return;
    lastStreamRefreshRef.current = now;
    loadInvestigation();
  }, [loadInvestigation]);

  useEffect(() => {
    loadInvestigation();

    const pollVisibleMs = 8000;
    const pollHiddenMs = 30000;
    let intervalId;

    const tick = () => {
      loadInvestigation();
    };

    const reschedule = () => {
      clearInterval(intervalId);
      const ms = document.visibilityState === 'hidden' ? pollHiddenMs : pollVisibleMs;
      intervalId = setInterval(tick, ms);
    };

    reschedule();
    document.addEventListener('visibilitychange', reschedule);

    return () => {
      document.removeEventListener('visibilitychange', reschedule);
      clearInterval(intervalId);
      clearInvestigation();
    };
  }, [loadInvestigation, clearInvestigation]);

  const handleInvestigationStarted = (data) => {
    setTimeout(loadInvestigation, 1000);
  };

  const handleSaveNotes = async () => {
    setSavingNotes(true);
    try {
      await axios.patch(`${API}/investigations/${id}`, { notes: caseNotes });
      toast.success('Case notes saved');
    } catch (error) {
      toast.error('Failed to save notes');
    } finally {
      setSavingNotes(false);
    }
  };

  const handleToggleStatus = async () => {
    const newStatus = investigation?.status === 'active' ? 'archived' : 'active';
    try {
      await axios.patch(`${API}/investigations/${id}`, { status: newStatus });
      setInvestigation({ ...investigation, status: newStatus });
      toast.success(`Investigation ${newStatus}`);
    } catch (error) {
      toast.error('Failed to update status');
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

  return (
    <div className="h-screen flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <header className="h-14 border-b border-white/5 flex items-center justify-between px-4 bg-black/50 backdrop-blur-sm flex-shrink-0 z-20">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white h-8 px-2 gap-1.5 text-xs"
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
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Users className="w-3 h-3" />
            <span>{entities.length}</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Network className="w-3 h-3" />
            <span>{relationships.length}</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <FileText className="w-3 h-3" />
            <span>{evidence.length}</span>
          </div>
          
          <Badge
            className={`cursor-pointer text-[10px] ${investigation?.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}
            onClick={handleToggleStatus}
            title="Click to toggle status"
          >
            {investigation?.status || 'active'}
          </Badge>
          <Button
            variant="ghost"
            className="text-slate-400 hover:text-white h-8 w-8 p-0"
            onClick={() => setShowCasePanel(!showCasePanel)}
            aria-label="Case notes"
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Case Notes Slide Panel */}
      {showCasePanel && (
        <div className="border-b border-white/5 bg-black/60 backdrop-blur-sm p-4 flex-shrink-0 z-10">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Case Notes</h3>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={handleSaveNotes} disabled={savingNotes} className="h-7 text-xs">
                <Save className="w-3 h-3 mr-1" />{savingNotes ? 'Saving...' : 'Save'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowCasePanel(false)} className="h-7 w-7 p-0">
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
          <textarea
            value={caseNotes}
            onChange={(e) => setCaseNotes(e.target.value)}
            className="w-full bg-black/50 border border-white/10 text-white text-sm rounded-sm p-3 min-h-[80px] max-h-[200px] resize-y placeholder:text-slate-600 focus:outline-none focus:border-primary/50"
            placeholder="Add investigation notes, hypotheses, analyst observations..."
          />
          <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-500">
            <span>Tags: {(investigation?.tags || []).join(', ') || 'none'}</span>
            <span>Created: {investigation?.created_at ? new Date(investigation.created_at).toLocaleDateString() : '-'}</span>
          </div>
        </div>
      )}

      {/* Universal Input */}
      <UniversalInput 
        investigationId={id} 
        onInvestigationStarted={handleInvestigationStarted}
      />

      {/* Main Content */}
      <main id="main-content" className="flex-1 flex overflow-hidden">
        {/* Left: Graph View */}
        <div className="flex-1 border-r border-white/5 bg-[#0a0a0a]">
          <GraphView 
            investigationId={id}
            onNavigateToEvidence={() => setRightPanel('evidence')}
            onNavigateToEntities={() => setRightPanel('entities')}
          />
        </div>

        {/* Right: Panels */}
        <aside className="w-96 bg-black/30 flex flex-col">
          {/* Panel Tabs */}
          <div className="flex border-b border-white/5 bg-black/20" role="tablist" aria-label="Investigation panels">
            <button
              role="tab"
              aria-selected={rightPanel === 'feed'}
              aria-controls="panel-feed"
              onClick={() => setRightPanel('feed')}
              className={`flex-1 px-4 py-3 text-xs font-medium transition-colors ${
                rightPanel === 'feed'
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Live Feed
            </button>
            <button
              role="tab"
              aria-selected={rightPanel === 'entities'}
              aria-controls="panel-entities"
              onClick={() => setRightPanel('entities')}
              className={`flex-1 px-4 py-3 text-xs font-medium transition-colors ${
                rightPanel === 'entities'
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Entities ({entities.length})
            </button>
            <button
              role="tab"
              aria-selected={rightPanel === 'evidence'}
              aria-controls="panel-evidence"
              onClick={() => setRightPanel('evidence')}
              className={`flex-1 px-4 py-3 text-xs font-medium transition-colors ${
                rightPanel === 'evidence'
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Evidence ({evidence.length})
            </button>
            <button
              role="tab"
              aria-selected={rightPanel === 'report'}
              aria-controls="panel-report"
              onClick={() => setRightPanel('report')}
              className={`flex-1 px-4 py-3 text-xs font-medium transition-colors ${
                rightPanel === 'report'
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Shield className="w-3 h-3 inline mr-1" />
              Report
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-hidden" role="tabpanel" id={`panel-${rightPanel}`}>
            {rightPanel === 'feed' && (
              <LiveFeed investigationId={id} onInvestigationDataMayHaveChanged={refreshFromStream} />
            )}
            {rightPanel === 'entities' && (
              <div className="h-full overflow-y-auto">
                <EntitiesWorkspace 
                  investigationId={id}
                  compact={true}
                  onNavigateToGraph={() => {}}
                  onNavigateToEvidence={() => setRightPanel('evidence')}
                />
              </div>
            )}
            {rightPanel === 'evidence' && (
              <div className="h-full overflow-y-auto">
                <EvidenceWorkspace 
                  investigationId={id}
                  compact={true}
                  onNavigateToEntities={() => setRightPanel('entities')}
                />
              </div>
            )}
            {rightPanel === 'report' && (
              <ReportView investigationId={id} />
            )}
          </div>
        </aside>
      </main>
    </div>
  );
};

export default UnifiedInvestigation;
