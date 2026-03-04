import React from 'react';
import { Clock, Plus, FileBox, Users, Link2, Sparkles, Network } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import useInvestigationStore from '../../store/investigationStore';

const EVENT_CONFIG = {
  ENTITY_ADDED: { icon: Users, color: '#14f195', label: 'Entity Added' },
  ENTITY_REMOVED: { icon: Users, color: '#ef4444', label: 'Entity Removed' },
  EDGE_CREATED: { icon: Link2, color: '#06b6d4', label: 'Connection Created' },
  EDGE_REMOVED: { icon: Link2, color: '#ef4444', label: 'Connection Removed' },
  EVIDENCE_ADDED: { icon: FileBox, color: '#fbbf24', label: 'Evidence Added' },
  EVIDENCE_REMOVED: { icon: FileBox, color: '#ef4444', label: 'Evidence Removed' },
  AI_SUGGESTION_ACCEPTED: { icon: Sparkles, color: '#7c3aed', label: 'AI Suggestion Accepted' },
  investigation_created: { icon: Network, color: '#06b6d4', label: 'Investigation Created' },
  entity_added: { icon: Users, color: '#14f195', label: 'Entity Added' },
  entity_removed: { icon: Users, color: '#ef4444', label: 'Entity Removed' },
  relationship_discovered: { icon: Link2, color: '#06b6d4', label: 'Connection Created' },
  evidence_added: { icon: FileBox, color: '#fbbf24', label: 'Evidence Added' },
  ai_analysis: { icon: Sparkles, color: '#7c3aed', label: 'AI Analysis' },
};

const TimelineWorkspace = ({ onNavigateToEvidence }) => {
  const { timeline, entities, relationships, evidence } = useInvestigationStore();

  const getEventConfig = (type) => EVENT_CONFIG[type] || { 
    icon: Clock, 
    color: '#94a3b8', 
    label: type?.replace(/_/g, ' ') || 'Event' 
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFullDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Group timeline by date
  const groupedTimeline = timeline.reduce((groups, event) => {
    const date = new Date(event.ts).toDateString();
    if (!groups[date]) groups[date] = [];
    groups[date].push(event);
    return groups;
  }, {});

  // Empty state
  if (timeline.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-slate-500/10 border border-slate-500/20 flex items-center justify-center mx-auto mb-6">
            <Clock className="w-10 h-10 text-slate-400" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            No Activity Yet
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            The timeline records every action in your investigation.
            Start by adding evidence to begin building your case.
          </p>

          <button 
            onClick={onNavigateToEvidence}
            className="px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Start Investigation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-heading font-bold text-white">Investigation Timeline</h2>
          <Badge variant="secondary" className="bg-white/5 text-slate-400 border-0">
            {timeline.length} events
          </Badge>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <FileBox className="w-3.5 h-3.5 text-amber-400" />
            <span>{evidence.length} evidence</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="w-3.5 h-3.5 text-emerald-400" />
            <span>{entities.length} entities</span>
          </div>
          <div className="flex items-center gap-2">
            <Link2 className="w-3.5 h-3.5 text-primary" />
            <span>{relationships.length} connections</span>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto">
          {Object.entries(groupedTimeline).map(([date, events]) => (
            <div key={date} className="mb-8">
              <div className="sticky top-0 bg-[#0a0a0a] py-2 z-10">
                <h3 className="text-sm font-medium text-slate-400">
                  {formatFullDate(events[0].ts)}
                </h3>
              </div>

              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-5 top-0 bottom-0 w-px bg-gradient-to-b from-primary/50 via-white/10 to-transparent"></div>

                <div className="space-y-4">
                  {events.map((event, index) => {
                    const config = getEventConfig(event.type);
                    const IconComponent = config.icon;

                    return (
                      <div 
                        key={event.id || index}
                        data-testid={`timeline-event-${event.id || index}`}
                        className="relative pl-14 group"
                      >
                        {/* Timeline dot */}
                        <div 
                          className="absolute left-2 top-1 w-6 h-6 rounded-full flex items-center justify-center border-2 border-[#0a0a0a] z-10 transition-transform group-hover:scale-110"
                          style={{ backgroundColor: config.color }}
                        >
                          <IconComponent className="w-3 h-3 text-black" />
                        </div>

                        {/* Event card */}
                        <div className="bg-black/40 border border-white/10 rounded-sm p-4 hover:border-white/20 transition-colors">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge 
                                  className="text-[10px] border-0"
                                  style={{ 
                                    backgroundColor: `${config.color}15`,
                                    color: config.color 
                                  }}
                                >
                                  {config.label}
                                </Badge>
                              </div>
                              <p className="text-white text-sm">{event.summary}</p>
                              
                              {event.meta && Object.keys(event.meta).length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {Object.entries(event.meta).map(([key, value]) => (
                                    <span key={key} className="text-xs text-slate-500">
                                      {key}: <span className="text-slate-400">{String(value)}</span>
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>

                            <span className="text-xs text-slate-500 font-mono whitespace-nowrap">
                              {formatDate(event.ts)}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TimelineWorkspace;
