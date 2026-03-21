import React, { useState } from 'react';
import { Sparkles, Zap, RefreshCw, CheckCircle, XCircle, Loader2, Plus, Link2, Users, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';

const SUGGESTION_CONFIG = {
  connection: { icon: Link2, color: '#06b6d4', label: 'Connection' },
  lead: { icon: AlertTriangle, color: '#14f195', label: 'Lead' },
  pattern: { icon: Sparkles, color: '#f97316', label: 'Pattern' },
  enrichment: { icon: Plus, color: '#7c3aed', label: 'Enrichment' },
};

const AISuggestionsWorkspace = ({ investigationId, onNavigateToEvidence }) => {
  const { entities, relationships, aiSuggestions, acceptAISuggestion, dismissAISuggestion, setAISuggestions, addEntity, addRelationship, setEntities, setRelationships } = useInvestigationStore();

  const [analyzing, setAnalyzing] = useState(false);
  const [mode, setMode] = useState('flash');

  const pendingSuggestions = aiSuggestions.filter(s => s.status !== 'accepted' && s.status !== 'dismissed');

  const runAnalysis = async () => {
    if (entities.length === 0) {
      toast.error('Add entities first before running AI analysis');
      return;
    }

    setAnalyzing(true);
    try {
      const response = await axios.post(`${API}/ai/analyze`, {
        investigation_id: investigationId,
        mode: mode,
        context: 'Analyze the current investigation and provide actionable suggestions for connections, leads, and patterns.'
      });

      if (response.data.success) {
        // Convert API suggestions to store format (use backend ids so accept/dismiss persists)
        const suggestions = response.data.suggestions?.map((sug) => {
          const actionData = sug.action_data || {};
          const actions = [];

          // Heuristic mapping so we can persist actions without breaking older payload shapes.
          if (actionData.entity_type && actionData.value) {
            actions.push({ kind: 'ADD_ENTITY', payload: actionData });
          } else if (actionData.source_entity_id && actionData.target_entity_id) {
            actions.push({ kind: 'ADD_EDGE', payload: actionData });
          } else if (Object.keys(actionData).length > 0) {
            actions.push({ kind: 'CUSTOM', payload: actionData });
          }

          return {
            id: sug.id,
            type: sug.suggestion_type || 'lead',
            title: sug.title,
            description: sug.description,
            confidence: sug.confidence || 0.7,
            action_data: actionData,
            actions,
            status: sug.status || 'pending',
            created_at: sug.created_at,
          };
        }) || [];

        // Keep existing non-duplicate suggestions (by backend id), then append the newest batch.
        const existingById = new Set(suggestions.map(s => s.id));
        const retained = aiSuggestions.filter(s => !existingById.has(s.id));
        setAISuggestions([...retained, ...suggestions]);
        toast.success(`AI analysis complete! ${response.data.suggestions_count || suggestions.length} suggestions generated`);
      }
    } catch (error) {
      console.error('AI analysis failed:', error);
      toast.error(error.response?.data?.detail || 'AI analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAccept = async (suggestionId) => {
    const suggestion = aiSuggestions.find(s => s.id === suggestionId);
    try {
      // Persist status change to backend
      await axios.patch(`${API}/investigations/${investigationId}/suggestions/${suggestionId}`, null, {
        params: { status: 'accepted' }
      });

      // Persist any ADD_ENTITY / ADD_EDGE actions carried in action_data
      if (suggestion?.actions?.length) {
        for (const action of suggestion.actions) {
          if (action.kind === 'ADD_ENTITY' && action.payload?.entity_type && action.payload?.value) {
            try {
              const res = await axios.post(`${API}/investigations/${investigationId}/entities`, action.payload);
              addEntity({
                id: res.data.id,
                kind: res.data.entity_type,
                value: res.data.value,
                label: res.data.label || res.data.value,
                notes: res.data.notes || '',
                tags: [],
                sources: res.data.sources || [],
                confidence: res.data.confidence || 0.5,
                risk: (res.data.risk_score || 0) * 100,
                createdAt: res.data.created_at,
              });
            } catch (e) {
              console.warn('Failed to persist ADD_ENTITY action:', e);
            }
          } else if (action.kind === 'ADD_EDGE' && action.payload?.source_entity_id && action.payload?.target_entity_id) {
            try {
              const res = await axios.post(`${API}/investigations/${investigationId}/relationships`, action.payload);
              addRelationship({
                id: res.data.id,
                fromId: res.data.source_entity_id,
                toId: res.data.target_entity_id,
                relType: res.data.relationship_type,
                label: res.data.label || res.data.relationship_type,
                confidence: res.data.confidence || 0.5,
                sources: [],
                createdAt: res.data.created_at,
              });
            } catch (e) {
              console.warn('Failed to persist ADD_EDGE action:', e);
            }
          }
        }
      }

      acceptAISuggestion(suggestionId);
      toast.success('Suggestion accepted');
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
      toast.error('Failed to accept suggestion');
    }
  };

  const handleDismiss = async (suggestionId) => {
    try {
      await axios.patch(`${API}/investigations/${investigationId}/suggestions/${suggestionId}`, null, {
        params: { status: 'dismissed' }
      });
      dismissAISuggestion(suggestionId);
      toast.success('Suggestion dismissed');
    } catch (error) {
      dismissAISuggestion(suggestionId);
    }
  };

  const getSuggestionConfig = (type) => SUGGESTION_CONFIG[type] || SUGGESTION_CONFIG.lead;

  // Empty state - not enough data
  if (entities.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mx-auto mb-6">
            <Sparkles className="w-10 h-10 text-violet-400" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            AI Investigation Assistant
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            The AI assistant analyzes your investigation data to suggest connections, leads, and patterns.
            Add evidence and entities first to enable AI analysis.
          </p>

          <Button 
            onClick={onNavigateToEvidence}
            className="bg-violet-500 hover:bg-violet-600 text-white"
          >
            <Plus className="w-4 h-4 mr-2" />
            Start Building Your Case
          </Button>

          <div className="mt-10 grid grid-cols-2 gap-3">
            {Object.entries(SUGGESTION_CONFIG).map(([key, config]) => (
              <div 
                key={key}
                className="p-3 rounded-sm bg-white/5 border border-white/5 flex items-center gap-3"
              >
                <config.icon className="w-4 h-4" style={{ color: config.color }} />
                <span className="text-xs text-slate-400">{config.label} Detection</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-violet-400" />
          <h2 className="text-lg font-heading font-bold text-white">AI Assistant</h2>
          {pendingSuggestions.length > 0 && (
            <Badge variant="secondary" className="bg-violet-500/10 text-violet-400 border-0">
              {pendingSuggestions.length} suggestions
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Mode Toggle */}
          <div className="flex border border-white/10 rounded-sm overflow-hidden">
            <button
              onClick={() => setMode('flash')}
              className={`px-3 py-1.5 text-xs font-medium transition-colors flex items-center gap-1.5 ${
                mode === 'flash'
                  ? 'bg-primary text-white'
                  : 'bg-transparent text-slate-400 hover:text-white'
              }`}
            >
              <Zap className="w-3 h-3" />
              Flash
            </button>
            <button
              onClick={() => setMode('pro')}
              className={`px-3 py-1.5 text-xs font-medium transition-colors flex items-center gap-1.5 ${
                mode === 'pro'
                  ? 'bg-primary text-white'
                  : 'bg-transparent text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              Pro
            </button>
          </div>

          <Button
            data-testid="run-ai-analysis-btn"
            onClick={runAnalysis}
            disabled={analyzing}
            className="bg-violet-500 hover:bg-violet-600 text-white text-xs h-8 rounded-sm"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                Run Analysis
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="p-4 border-b border-white/5">
        <div className="bg-violet-500/5 border border-violet-500/20 rounded-sm p-4 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-violet-400 mt-0.5" />
          <div>
            <p className="text-sm text-white mb-1">
              Analyzing {entities.length} entities and {relationships.length} connections
            </p>
            <p className="text-xs text-slate-400">
              <span className="text-violet-400 font-medium">Flash:</span> Quick analysis • 
              <span className="text-violet-400 font-medium ml-2">Pro:</span> Deep analysis with enhanced reasoning
            </p>
          </div>
        </div>
      </div>

      {/* Suggestions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {pendingSuggestions.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full bg-violet-500/10 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-violet-400" />
            </div>
            <h3 className="text-lg font-heading font-bold text-white mb-2">Ready to Analyze</h3>
            <p className="text-sm text-slate-400 mb-6">
              Click "Run Analysis" to get AI-powered suggestions
            </p>
            <Button
              onClick={runAnalysis}
              disabled={analyzing}
              className="bg-violet-500 hover:bg-violet-600 text-white"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Start Analysis
                </>
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {pendingSuggestions.map(suggestion => {
              const config = getSuggestionConfig(suggestion.type);

              return (
                <div 
                  key={suggestion.id}
                  data-testid={`suggestion-card-${suggestion.id}`}
                  className="bg-black/40 border border-white/10 rounded-sm overflow-hidden hover:border-violet-500/30 transition-colors"
                >
                  <div className="p-5">
                    <div className="flex items-start gap-4">
                      <div 
                        className="w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: `${config.color}15`, border: `1px solid ${config.color}30` }}
                      >
                        <config.icon className="w-5 h-5" style={{ color: config.color }} />
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-white font-medium">{suggestion.title}</h3>
                          <Badge 
                            className="text-[10px] border-0"
                            style={{ 
                              backgroundColor: `${config.color}15`,
                              color: config.color 
                            }}
                          >
                            {config.label}
                          </Badge>
                          {suggestion.confidence && (
                            <span className="text-xs text-slate-500">
                              {Math.round(suggestion.confidence * 100)}% confidence
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-slate-400 leading-relaxed">
                          {suggestion.description}
                        </p>

                        {suggestion.actions?.length > 0 && suggestion.actions[0]?.payload && Object.keys(suggestion.actions[0].payload).length > 0 && (
                          <div className="mt-3 p-3 bg-white/5 rounded-sm border border-white/5">
                            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Action Data</p>
                            <pre className="text-xs text-primary font-mono overflow-x-auto">
                              {JSON.stringify(suggestion.actions[0].payload, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="px-5 py-3 border-t border-white/5 bg-white/[0.02] flex items-center gap-2">
                    <Button
                      data-testid={`accept-suggestion-${suggestion.id}`}
                      onClick={() => handleAccept(suggestion.id)}
                      size="sm"
                      className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs h-8"
                    >
                      <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                      Accept
                    </Button>
                    <Button
                      data-testid={`dismiss-suggestion-${suggestion.id}`}
                      onClick={() => handleDismiss(suggestion.id)}
                      size="sm"
                      variant="ghost"
                      className="text-slate-400 hover:text-white hover:bg-white/5 text-xs h-8"
                    >
                      <XCircle className="w-3.5 h-3.5 mr-1.5" />
                      Dismiss
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-slate-400 hover:text-white hover:bg-white/5 text-xs h-8 ml-auto"
                    >
                      Investigate
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AISuggestionsWorkspace;
