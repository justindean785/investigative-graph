import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Sparkles, Zap, RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { API } from '../App';

const AISuggestionsTab = ({ investigationId, refreshTrigger, onRefresh }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [mode, setMode] = useState('flash');

  useEffect(() => {
    fetchSuggestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investigationId, refreshTrigger]);

  const fetchSuggestions = async () => {
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/suggestions`);
      setSuggestions(response.data);
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      toast.error('Failed to load AI suggestions');
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      const response = await axios.post(`${API}/ai/analyze`, {
        investigation_id: investigationId,
        mode: mode,
        context: 'Analyze the current investigation and provide actionable suggestions'
      });

      if (response.data.success) {
        toast.success(`AI analysis complete! ${response.data.suggestions_count} suggestions generated`);
        fetchSuggestions();
        onRefresh();
      }
    } catch (error) {
      console.error('AI analysis failed:', error);
      toast.error(error.response?.data?.detail || 'AI analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const acceptSuggestion = async (suggestionId) => {
    try {
      await axios.patch(`${API}/investigations/${investigationId}/suggestions/${suggestionId}`, null, {
        params: { status: 'accepted' }
      });
      toast.success('Suggestion accepted');
      fetchSuggestions();
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
      toast.error('Failed to accept suggestion');
    }
  };

  const dismissSuggestion = async (suggestionId) => {
    try {
      await axios.patch(`${API}/investigations/${investigationId}/suggestions/${suggestionId}`, null, {
        params: { status: 'dismissed' }
      });
      toast.success('Suggestion dismissed');
      fetchSuggestions();
    } catch (error) {
      console.error('Failed to dismiss suggestion:', error);
      toast.error('Failed to dismiss suggestion');
    }
  };

  const getSuggestionIcon = (type) => {
    const icons = {
      connection: '🔗',
      lead: '🎯',
      pattern: '🔍',
      enrichment: '📊'
    };
    return icons[type] || '💡';
  };

  const getSuggestionColor = (type) => {
    const colors = {
      connection: 'bg-[#00d9ff]/20 text-[#00d9ff] border-[#00d9ff]/30',
      lead: 'bg-[#14f195]/20 text-[#14f195] border-[#14f195]/30',
      pattern: 'bg-[#f97316]/20 text-[#f97316] border-[#f97316]/30',
      enrichment: 'bg-[#7c3aed]/20 text-[#7c3aed] border-[#7c3aed]/30'
    };
    return colors[type] || 'bg-[#94a3b8]/20 text-[#94a3b8] border-[#94a3b8]/30';
  };

  return (
    <div className="h-full glass border border-[#00d9ff]/20 rounded-lg p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Sparkles className="w-6 h-6 text-[#00d9ff]" />
          <h2 className="text-2xl font-bold text-[#00d9ff]">AI Investigation Assistant</h2>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex border border-[#00d9ff]/20 rounded-md overflow-hidden">
            <button
              onClick={() => setMode('flash')}
              className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
                mode === 'flash'
                  ? 'bg-[#00d9ff] text-black'
                  : 'bg-transparent text-[#94a3b8] hover:text-white'
              }`}
            >
              <Zap className="w-3 h-3 inline mr-1" />
              Flash
            </button>
            <button
              onClick={() => setMode('pro')}
              className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
                mode === 'pro'
                  ? 'bg-[#00d9ff] text-black'
                  : 'bg-transparent text-[#94a3b8] hover:text-white'
              }`}
            >
              <Sparkles className="w-3 h-3 inline mr-1" />
              Pro
            </button>
          </div>

          <Button
            data-testid="run-ai-analysis-btn"
            onClick={runAnalysis}
            disabled={analyzing}
            className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] shadow-[0_0_15px_rgba(0,217,255,0.3)] font-bold uppercase text-xs"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Run Analysis
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="mb-6 bg-[#0d1b2a]/50 border border-[#00d9ff]/20 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-[#00d9ff] mt-1" />
          <div>
            <p className="text-white text-sm mb-2">
              The AI assistant analyzes your investigation data and provides actionable suggestions for new leads, connections, and enrichment opportunities.
            </p>
            <p className="text-[#94a3b8] text-xs">
              <strong className="text-[#00d9ff]">Flash Mode:</strong> Quick analysis • 
              <strong className="text-[#00d9ff] ml-2">Pro Mode:</strong> Deep analysis with enhanced reasoning
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
        </div>
      ) : suggestions.length === 0 ? (
        <div className="text-center py-20">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-[#00d9ff]/10 mb-4">
            <Sparkles className="w-10 h-10 text-[#00d9ff]" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">No Suggestions Yet</h3>
          <p className="text-[#94a3b8] mb-6">Run AI analysis to get investigative suggestions</p>
          <Button
            onClick={runAnalysis}
            disabled={analyzing}
            className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Run First Analysis
              </>
            )}
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {suggestions.map(suggestion => (
            <div
              key={suggestion.id}
              data-testid={`suggestion-card-${suggestion.id}`}
              className="bg-[#0d1b2a]/50 border border-[#00d9ff]/20 rounded-lg p-5 hover:border-[#00d9ff]/40 transition-all duration-300 hover:shadow-[0_0_15px_rgba(0,217,255,0.15)]"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3 flex-1">
                  <div className="text-3xl">{getSuggestionIcon(suggestion.suggestion_type)}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-bold text-white">{suggestion.title}</h3>
                      <Badge className={`border text-xs ${getSuggestionColor(suggestion.suggestion_type)}`}>
                        {suggestion.suggestion_type}
                      </Badge>
                    </div>
                    <p className="text-sm text-[#94a3b8] leading-relaxed">{suggestion.description}</p>
                  </div>
                </div>
              </div>

              {suggestion.action_data && Object.keys(suggestion.action_data).length > 0 && (
                <div className="mt-4 pt-4 border-t border-[#00d9ff]/10">
                  <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-2">Action Data</p>
                  <div className="bg-[#0a1628]/50 rounded p-3 font-mono text-xs text-[#00d9ff]">
                    <pre className="whitespace-pre-wrap">{JSON.stringify(suggestion.action_data, null, 2)}</pre>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 mt-4">
                <Button
                  data-testid={`accept-suggestion-${suggestion.id}`}
                  onClick={() => acceptSuggestion(suggestion.id)}
                  size="sm"
                  className="bg-[#14f195] text-black hover:bg-[#14f195]/80 font-bold uppercase text-xs"
                >
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Accept
                </Button>
                <Button
                  data-testid={`dismiss-suggestion-${suggestion.id}`}
                  onClick={() => dismissSuggestion(suggestion.id)}
                  size="sm"
                  variant="ghost"
                  className="text-[#94a3b8] hover:text-white hover:bg-[#94a3b8]/10 font-bold uppercase text-xs"
                >
                  <XCircle className="w-3 h-3 mr-1" />
                  Dismiss
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AISuggestionsTab;
