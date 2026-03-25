import React, { useState, useEffect, useMemo } from 'react';
import { Lightbulb, RefreshCw, Search, ChevronRight, AlertTriangle, Link2, Users, Wallet, Globe, Clock, CheckCircle, XCircle, Eye, Loader2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';

const LEAD_TYPE_CONFIG = {
  alias_cluster: {
    icon: Users,
    color: '#f97316',
    label: 'Alias Cluster',
    description: 'Multiple identities potentially linked'
  },
  wallet_cluster: {
    icon: Wallet,
    color: '#fbbf24',
    label: 'Wallet Cluster',
    description: 'Cryptocurrency wallets showing coordinated activity'
  },
  shared_infrastructure: {
    icon: Globe,
    color: '#06b6d4',
    label: 'Shared Infrastructure',
    description: 'Common hosting or registration patterns'
  },
  username_reuse: {
    icon: Users,
    color: '#14f195',
    label: 'Username Reuse',
    description: 'Same username pattern across platforms'
  },
  high_risk_connection: {
    icon: AlertTriangle,
    color: '#ef4444',
    label: 'High-Risk Network',
    description: 'Entity connected to multiple high-risk items'
  },
  timing_anomaly: {
    icon: Clock,
    color: '#7c3aed',
    label: 'Timing Anomaly',
    description: 'Suspicious activity patterns detected'
  },
  missing_connection: {
    icon: Link2,
    color: '#3b82f6',
    label: 'Potential Connection',
    description: 'Possible hidden relationship to investigate'
  }
};

const SEVERITY_CONFIG = {
  critical: { color: '#ef4444', bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' },
  high: { color: '#f97316', bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400' },
  medium: { color: '#fbbf24', bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400' },
  low: { color: '#06b6d4', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', text: 'text-cyan-400' }
};

const LeadsWorkspace = ({ investigationId, onNavigateToEvidence, onNavigateToEntities, searchQuery = '' }) => {
  const { entities, relationships } = useInvestigationStore();
  
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [expandedLead, setExpandedLead] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investigationId]);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/leads`);
      setLeads(response.data.leads || []);
    } catch (error) {
      console.error('Failed to fetch leads:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateLeads = async () => {
    if (entities.length === 0) {
      toast.error('Add entities to your investigation first');
      return;
    }

    setGenerating(true);
    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/leads/generate`);
      if (response.data.success) {
        setLeads(response.data.leads || []);
        toast.success(`Generated ${response.data.leads_generated} investigation leads`);
      }
    } catch (error) {
      console.error('Failed to generate leads:', error);
      toast.error('Failed to generate leads');
    } finally {
      setGenerating(false);
    }
  };

  const updateLeadStatus = async (leadId, status) => {
    try {
      await axios.patch(`${API}/investigations/${investigationId}/leads/${leadId}`, null, {
        params: { status }
      });
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status } : l));
      toast.success(`Lead marked as ${status}`);
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  const getLeadTypeConfig = (type) => LEAD_TYPE_CONFIG[type] || {
    icon: Lightbulb,
    color: '#94a3b8',
    label: type.replace(/_/g, ' '),
    description: 'Investigation lead'
  };

  const q = (searchQuery || '').trim().toLowerCase();

  const filteredLeads = useMemo(() => {
    let list = statusFilter === 'all' ? leads : leads.filter((l) => l.status === statusFilter);
    if (q) {
      list = list.filter(
        (l) =>
          (l.title || '').toLowerCase().includes(q) ||
          (l.description || '').toLowerCase().includes(q) ||
          (l.lead_type || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [leads, statusFilter, q]);

  const leadsByStatus = {
    new: leads.filter(l => l.status === 'new').length,
    investigating: leads.filter(l => l.status === 'investigating').length,
    confirmed: leads.filter(l => l.status === 'confirmed').length,
    dismissed: leads.filter(l => l.status === 'dismissed').length
  };

  // Empty state - no entities yet
  if (entities.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6">
            <Lightbulb className="w-10 h-10 text-amber-400" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            Investigation Lead Engine
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            The lead engine analyzes your investigation data to automatically generate hypotheses and discover hidden patterns.
            Start by adding evidence and entities to enable automated lead generation.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button 
              onClick={onNavigateToEvidence}
              className="bg-primary hover:bg-primary/90 text-white"
            >
              <Zap className="w-4 h-4 mr-2" />
              Add Evidence
            </Button>
            
            <Button 
              onClick={onNavigateToEntities}
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/5"
            >
              <Users className="w-4 h-4 mr-2" />
              Add Entities
            </Button>
          </div>

          <div className="mt-10 p-5 bg-white/5 rounded-sm border border-white/10 text-left">
            <p className="text-xs text-amber-400/80 uppercase tracking-wider mb-3 font-semibold">Lead Types Detected</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(LEAD_TYPE_CONFIG).slice(0, 6).map(([key, config]) => (
                <div key={key} className="flex items-center gap-2 text-xs text-slate-400">
                  <config.icon className="w-3.5 h-3.5" style={{ color: config.color }} />
                  <span>{config.label}</span>
                </div>
              ))}
            </div>
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
          <Lightbulb className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-heading font-bold text-white">Investigation Leads</h2>
          {leads.length > 0 && (
            <Badge variant="secondary" className="bg-amber-500/10 text-amber-400 border-0">
              {leads.length} leads
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            data-testid="generate-leads-btn"
            onClick={generateLeads}
            disabled={generating}
            className="bg-amber-500 hover:bg-amber-600 text-black text-xs h-8 rounded-sm"
          >
            {generating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                Generate Leads
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="p-4 border-b border-white/5 bg-black/30">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
              statusFilter === 'all' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            All ({leads.length})
          </button>
          <button
            onClick={() => setStatusFilter('new')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors flex items-center gap-1.5 ${
              statusFilter === 'new' ? 'bg-amber-500/10 text-amber-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <div className="w-2 h-2 rounded-full bg-amber-400"></div>
            New ({leadsByStatus.new})
          </button>
          <button
            onClick={() => setStatusFilter('investigating')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors flex items-center gap-1.5 ${
              statusFilter === 'investigating' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Eye className="w-3 h-3" />
            Investigating ({leadsByStatus.investigating})
          </button>
          <button
            onClick={() => setStatusFilter('confirmed')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors flex items-center gap-1.5 ${
              statusFilter === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <CheckCircle className="w-3 h-3" />
            Confirmed ({leadsByStatus.confirmed})
          </button>
        </div>
      </div>

      {/* Leads List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-16">
            <Loader2 className="w-8 h-8 text-amber-400 animate-spin mx-auto mb-4" />
            <p className="text-slate-400">Loading leads...</p>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-amber-400" />
            </div>
            <h3 className="text-lg font-heading font-bold text-white mb-2">
              {leads.length === 0 ? 'No Leads Generated' : 'No Matching Leads'}
            </h3>
            <p className="text-sm text-slate-400 mb-6">
              {leads.length === 0 
                ? 'Click "Generate Leads" to analyze your investigation data and discover patterns.'
                : 'Try a different filter or generate new leads.'}
            </p>
            {leads.length === 0 && (
              <Button
                onClick={generateLeads}
                disabled={generating}
                className="bg-amber-500 hover:bg-amber-600 text-black"
              >
                <Lightbulb className="w-4 h-4 mr-2" />
                Generate Leads
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {filteredLeads.map(lead => {
              const typeConfig = getLeadTypeConfig(lead.lead_type);
              const severityConfig = SEVERITY_CONFIG[lead.severity] || SEVERITY_CONFIG.medium;
              const isExpanded = expandedLead === lead.id;
              const confidencePercent = Math.round((lead.confidence || 0.5) * 100);

              return (
                <div 
                  key={lead.id}
                  data-testid={`lead-card-${lead.id}`}
                  className={`bg-black/40 border rounded-sm overflow-hidden transition-all ${
                    isExpanded ? `${severityConfig.border} border-opacity-100` : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  {/* Lead Header */}
                  <div 
                    className="p-5 cursor-pointer"
                    onClick={() => setExpandedLead(isExpanded ? null : lead.id)}
                  >
                    <div className="flex items-start gap-4">
                      {/* Type Icon */}
                      <div 
                        className={`w-12 h-12 rounded-sm flex items-center justify-center flex-shrink-0 ${severityConfig.bg}`}
                        style={{ border: `1px solid ${typeConfig.color}40` }}
                      >
                        <typeConfig.icon className="w-6 h-6" style={{ color: typeConfig.color }} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <h3 className="text-white font-medium">{lead.title}</h3>
                          <Badge 
                            className={`text-[10px] border-0 ${severityConfig.bg} ${severityConfig.text}`}
                          >
                            {lead.severity?.toUpperCase()}
                          </Badge>
                          <Badge 
                            className="text-[10px] border-0 bg-white/5 text-slate-400"
                          >
                            {typeConfig.label}
                          </Badge>
                          {lead.status !== 'new' && (
                            <Badge 
                              className={`text-[10px] border-0 ${
                                lead.status === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' :
                                lead.status === 'investigating' ? 'bg-blue-500/10 text-blue-400' :
                                'bg-slate-500/10 text-slate-400'
                              }`}
                            >
                              {lead.status}
                            </Badge>
                          )}
                        </div>

                        <p className="text-sm text-slate-400 leading-relaxed mb-3">
                          {lead.description}
                        </p>

                        {/* Confidence Bar */}
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500">Confidence</span>
                          <div className="flex-1 max-w-32 h-1.5 bg-black/50 rounded-full overflow-hidden">
                            <div 
                              className="h-full rounded-full transition-all"
                              style={{ 
                                width: `${confidencePercent}%`,
                                backgroundColor: confidencePercent >= 75 ? '#14f195' : 
                                                 confidencePercent >= 50 ? '#fbbf24' : '#f97316'
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono text-slate-400">{confidencePercent}%</span>
                          
                          {lead.affected_entities?.length > 0 && (
                            <span className="text-xs text-slate-500 ml-4">
                              {lead.affected_entities.length} entities involved
                            </span>
                          )}
                        </div>
                      </div>

                      <ChevronRight className={`w-5 h-5 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="px-5 pb-5 border-t border-white/5 bg-white/[0.02]">
                      {/* Metadata */}
                      {lead.metadata && Object.keys(lead.metadata).length > 0 && (
                        <div className="mt-4 p-4 bg-black/30 rounded-sm border border-white/5">
                          <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Analysis Details</p>
                          <div className="grid grid-cols-2 gap-3">
                            {Object.entries(lead.metadata).map(([key, value]) => (
                              <div key={key}>
                                <span className="text-xs text-slate-500">{key.replace(/_/g, ' ')}</span>
                                <p className="text-sm text-white font-mono truncate">
                                  {Array.isArray(value) ? value.join(', ') : String(value)}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Suggested Actions */}
                      {lead.suggested_actions?.length > 0 && (
                        <div className="mt-4">
                          <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Suggested Actions</p>
                          <div className="flex flex-wrap gap-2">
                            {lead.suggested_actions.map((action, idx) => (
                              <Button
                                key={idx}
                                variant="outline"
                                size="sm"
                                className="border-white/10 text-slate-300 hover:bg-white/5 text-xs h-8"
                              >
                                {action.type === 'investigate' && <Eye className="w-3 h-3 mr-1.5" />}
                                {action.type === 'connect' && <Link2 className="w-3 h-3 mr-1.5" />}
                                {action.type === 'search' && <Search className="w-3 h-3 mr-1.5" />}
                                {action.type === 'enrich' && <Zap className="w-3 h-3 mr-1.5" />}
                                {action.label}
                              </Button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Status Actions */}
                      <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-2">
                        {lead.status === 'new' && (
                          <>
                            <Button
                              onClick={() => updateLeadStatus(lead.id, 'investigating')}
                              size="sm"
                              className="bg-blue-500 hover:bg-blue-600 text-white text-xs h-8"
                            >
                              <Eye className="w-3.5 h-3.5 mr-1.5" />
                              Investigate
                            </Button>
                            <Button
                              onClick={() => updateLeadStatus(lead.id, 'confirmed')}
                              size="sm"
                              className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs h-8"
                            >
                              <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                              Confirm
                            </Button>
                            <Button
                              onClick={() => updateLeadStatus(lead.id, 'dismissed')}
                              size="sm"
                              variant="ghost"
                              className="text-slate-400 hover:text-white text-xs h-8"
                            >
                              <XCircle className="w-3.5 h-3.5 mr-1.5" />
                              Dismiss
                            </Button>
                          </>
                        )}
                        {lead.status === 'investigating' && (
                          <>
                            <Button
                              onClick={() => updateLeadStatus(lead.id, 'confirmed')}
                              size="sm"
                              className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs h-8"
                            >
                              <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                              Confirm Lead
                            </Button>
                            <Button
                              onClick={() => updateLeadStatus(lead.id, 'dismissed')}
                              size="sm"
                              variant="ghost"
                              className="text-slate-400 hover:text-white text-xs h-8"
                            >
                              <XCircle className="w-3.5 h-3.5 mr-1.5" />
                              Dismiss
                            </Button>
                          </>
                        )}
                        {(lead.status === 'confirmed' || lead.status === 'dismissed') && (
                          <Button
                            onClick={() => updateLeadStatus(lead.id, 'new')}
                            size="sm"
                            variant="outline"
                            className="border-white/10 text-slate-300 hover:bg-white/5 text-xs h-8"
                          >
                            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                            Reset Status
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default LeadsWorkspace;
