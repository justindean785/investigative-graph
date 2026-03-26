import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, Zap, CheckCircle, AlertCircle, TrendingUp, Link2, FileText, Pause, Play } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { BACKEND_URL } from '@/config/api';
import axios from '@/config/api';

const EVENT_ICONS = {
  entity_discovered: TrendingUp,
  enrichment_started: Activity,
  enrichment_completed: CheckCircle,
  relationship_created: Link2,
  evidence_added: FileText,
  pivot_selected: Zap,
  investigation_paused: Pause,
  investigation_completed: CheckCircle,
  error: AlertCircle,
};

const EVENT_COLORS = {
  entity_discovered: '#14f195',
  enrichment_started: '#06b6d4',
  enrichment_completed: '#10b981',
  relationship_created: '#3b82f6',
  evidence_added: '#fbbf24',
  pivot_selected: '#7c3aed',
  investigation_paused: '#f97316',
  investigation_completed: '#22c55e',
  error: '#ef4444',
};

const STREAM_INVALIDATE_TYPES = new Set([
  'entity_discovered',
  'enrichment_completed',
  'relationship_created',
  'evidence_added',
  'progress',
  'investigation_completed',
  'error',
]);

const LiveFeed = ({ investigationId, onInvestigationDataMayHaveChanged }) => {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const feedEndRef = useRef(null);

  const retryTimeoutRef = useRef(null);
  const retryDelayMsRef = useRef(3000);

  const addEvent = useCallback((eventType, message, data = {}) => {
    const newEvent = {
      id: `evt-${Date.now()}-${Math.random()}`,
      type: eventType,
      message,
      timestamp: new Date().toISOString(),
      data
    };
    setEvents(prev => [newEvent, ...prev]);
  }, []);

  const maybeNotifyDataChanged = useCallback(
    (eventType) => {
      if (!onInvestigationDataMayHaveChanged) return;
      if (STREAM_INVALIDATE_TYPES.has(eventType)) {
        onInvestigationDataMayHaveChanged();
      }
    },
    [onInvestigationDataMayHaveChanged]
  );

  const connectToStream = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    let streamToken;
    try {
      const { data } = await axios.post(
        `${BACKEND_URL}/api/investigations/${investigationId}/stream-token`
      );
      streamToken = data.stream_token;
    } catch (err) {
      console.error('Failed to obtain stream token:', err);
      const delay = retryDelayMsRef.current;
      retryDelayMsRef.current = Math.min(Math.round(delay * 1.5), 30000);
      retryTimeoutRef.current = setTimeout(connectToStream, delay);
      return;
    }

    const eventSource = new EventSource(
      `${BACKEND_URL}/api/investigations/${investigationId}/stream?stream_token=${encodeURIComponent(streamToken)}`
    );

    eventSource.onopen = () => {
      setIsConnected(true);
      retryDelayMsRef.current = 3000;
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.event_type || 'update';
        addEvent(
          eventType,
          data.message || 'Investigation update',
          data.data || {}
        );
        maybeNotifyDataChanged(eventType);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.addEventListener('connected', (event) => {
      const data = JSON.parse(event.data);
      addEvent('connected', 'Connected to investigation stream', data);
      setIsConnected(true);
    });

    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data);
      addEvent('progress', `Processed: ${data.processed_count}, Discovered: ${data.entities_discovered}`, data);
      maybeNotifyDataChanged('progress');
    });

    eventSource.addEventListener('completed', (event) => {
      const data = JSON.parse(event.data);
      addEvent('investigation_completed', 'Investigation completed', data);
      maybeNotifyDataChanged('investigation_completed');
      setIsConnected(false);
      eventSource.close();
    });

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      setIsConnected(false);
      eventSource.close();
      const delay = retryDelayMsRef.current;
      retryDelayMsRef.current = Math.min(Math.round(delay * 1.5), 30000);
      retryTimeoutRef.current = setTimeout(connectToStream, delay);
    };

    eventSourceRef.current = eventSource;
  }, [investigationId, addEvent, maybeNotifyDataChanged]);

  useEffect(() => {
    connectToStream();
    
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connectToStream]);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <Activity className="w-12 h-12 text-slate-600 mb-4" />
        <p className="text-sm text-slate-400">Start an investigation to see live updates</p>
        <p className="text-xs text-slate-500 mt-2">The AI will report progress in real-time</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Connection Status */}
      <div className="p-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-slate-600'} animate-pulse`} />
          <span className="text-xs text-slate-400">
            {isConnected ? 'Live' : 'Connecting...'}
          </span>
        </div>
        
        <Badge variant="secondary" className="text-[10px] bg-white/5 text-slate-400 border-0">
          {events.length} events
        </Badge>
      </div>

      {/* Events Feed */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {events.map((event) => {
          const Icon = EVENT_ICONS[event.type] || Activity;
          const color = EVENT_COLORS[event.type] || '#64748b';
          
          return (
            <div
              key={event.id}
              className="flex items-start gap-3 p-3 rounded-sm bg-white/[0.02] hover:bg-white/[0.04] transition-colors border border-white/5"
            >
              <div 
                className="w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${color}15`, borderColor: `${color}30` }}
              >
                <Icon className="w-4 h-4" style={{ color }} />
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white leading-tight">{event.message}</p>
                
                {event.data && Object.keys(event.data).length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-2">
                    {Object.entries(event.data).map(([key, value]) => (
                      <span
                        key={key}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400"
                      >
                        {key}: {JSON.stringify(value)}
                      </span>
                    ))}
                  </div>
                )}
                
                <time className="text-[10px] text-slate-600 mt-1 block">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </time>
              </div>
            </div>
          );
        })}
        
        <div ref={feedEndRef} />
      </div>
    </div>
  );
};

export default LiveFeed;
