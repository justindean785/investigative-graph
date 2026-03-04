import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Clock, Circle } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../App';

const TimelineTab = ({ investigationId, refreshTrigger }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTimeline();
  }, [investigationId, refreshTrigger]);

  const fetchTimeline = async () => {
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/timeline`);
      setEvents(response.data);
    } catch (error) {
      console.error('Failed to fetch timeline:', error);
      toast.error('Failed to load timeline');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getEventColor = (type) => {
    const colors = {
      investigation_created: '#00d9ff',
      entity_added: '#14f195',
      entity_removed: '#ff3b30',
      relationship_discovered: '#00d9ff',
      evidence_added: '#fbbf24',
      ai_analysis: '#7c3aed',
      enrichment_run: '#3b82f6'
    };
    return colors[type] || '#94a3b8';
  };

  const getEventIcon = (type) => {
    const icons = {
      investigation_created: '📁',
      entity_added: '➕',
      entity_removed: '🗑️',
      relationship_discovered: '🔗',
      evidence_added: '📎',
      ai_analysis: '✨',
      enrichment_run: '🔍'
    };
    return icons[type] || '📍';
  };

  return (
    <div className="h-full glass border border-[#00d9ff]/20 rounded-lg p-6 overflow-y-auto">
      <div className="flex items-center gap-3 mb-6">
        <Clock className="w-6 h-6 text-[#00d9ff]" />
        <h2 className="text-2xl font-bold text-[#00d9ff]">Investigation Timeline</h2>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-20">
          <Clock className="w-16 h-16 text-[#94a3b8] mx-auto mb-4 opacity-50" />
          <p className="text-[#94a3b8]">No timeline events yet</p>
        </div>
      ) : (
        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#00d9ff] to-transparent"></div>

          <div className="space-y-6">
            {events.map((event, index) => (
              <div
                key={event.id}
                data-testid={`timeline-event-${event.id}`}
                className="relative pl-20 group"
              >
                {/* Timeline Dot */}
                <div
                  className="absolute left-5 top-2 w-6 h-6 rounded-full border-4 border-[#0a1628] flex items-center justify-center text-xs group-hover:scale-110 transition-transform"
                  style={{
                    backgroundColor: getEventColor(event.event_type),
                    boxShadow: `0 0 10px ${getEventColor(event.event_type)}80`
                  }}
                >
                  {getEventIcon(event.event_type)}
                </div>

                {/* Event Card */}
                <div className="bg-[#0d1b2a]/50 border border-[#00d9ff]/20 rounded-lg p-4 hover:border-[#00d9ff]/40 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-white font-medium">{event.description}</h3>
                      <p className="text-xs text-[#94a3b8] mt-1 uppercase tracking-wider">
                        {event.event_type.replace('_', ' ')}
                      </p>
                    </div>
                    <p className="text-xs text-[#94a3b8] font-mono">
                      {formatDate(event.timestamp)}
                    </p>
                  </div>

                  {event.metadata && Object.keys(event.metadata).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[#00d9ff]/10">
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(event.metadata).map(([key, value]) => (
                          <div key={key} className="text-xs">
                            <span className="text-[#94a3b8]">{key}:</span>
                            <span className="text-white ml-1 font-mono">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineTab;
