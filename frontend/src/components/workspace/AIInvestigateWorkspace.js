import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Brain, Zap, Search, Shield, Globe, Database, AlertTriangle, CheckCircle, Clock, ChevronRight, User, Mail, Phone, Server, Wallet, Hash, Link, Twitter, Loader2, Play, StopCircle, Sparkles, TrendingUp, Eye, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';

const ENTITY_ICONS = {
  username: Twitter, email: Mail, phone: Phone, domain: Globe,
  ip: Server, wallet: Wallet, person: User, company: Target,
  social: Link, url: Globe, hash: Hash, default: Search,
};

const ENTITY_COLORS = {
  username: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  email: 'text-green-400 bg-green-400/10 border-green-400/30',
  phone: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
  domain: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
  ip: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  wallet: 'text-red-400 bg-red-400/10 border-red-400/30',
  person: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30',
  social: 'text-pink-400 bg-pink-400/10 border-pink-400/30',
  default: 'text-gray-400 bg-gray-400/10 border-gray-400/30',
};

const SEVERITY_COLORS = {
  critical: 'text-red-400 bg-red-400/10 border-red-400/40',
  high: 'text-orange-400 bg-orange-400/10 border-orange-400/40',
  medium: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/40',
  low: 'text-green-400 bg-green-400/10 border-green-400/40',
};

const SCAN_ICONS = {
  bosint_username: '🔍',
  bosint_email: '📧',
  bosint_domain: '🌐',
  bosint_ip: '🖥️',
  bosint_phone: '📱',
  swatted_breach: '💀',
  email_breach: '🔓',
  darkweb_search: '🕸️',
  perplexity_search: '🧠',
  default: '⚡',
};

const EXAMPLE_QUERIES = [
  { label: 'Username', value: 'shadowhunter77', icon: '👤' },
  { label: 'Email', value: 'user@example.com', icon: '📧' },
  { label: 'Domain', value: 'suspicious-domain.com', icon: '🌐' },
  { label: 'IP Address', value: '192.168.1.1', icon: '🖥️' },
  { label: 'Wallet', value: '0x742d35Cc6634C0532925a3b8D4C9C6d1f6c1a1b2', icon: '💰' },
];

export default function AIInvestigateWorkspace({ investigationId, onEntitiesUpdated }) {
  const [inputText, setInputText] = useState('');
  const [scanDepth, setScanDepth] = useState('standard');
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState([]);
  const [entities, setEntities] = useState([]);
  const [leads, setLeads] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [stats, setStats] = useState(null);
  const [currentPhase, setCurrentPhase] = useState('');
  const [activeScan, setActiveScan] = useState(null);
  const [hasRun, setHasRun] = useState(false);
  const eventSourceRef = useRef(null);
  const logEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  const stopInvestigation = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsRunning(false);
    setActiveScan(null);
  }, []);

  const startInvestigation = async () => {
    if (!inputText.trim()) {
      toast.error('Enter a username, email, domain, IP, or other identifier');
      return;
    }
    stopInvestigation();
    setEvents([]);
    setEntities([]);
    setLeads([]);
    setRelationships([]);
    setStats(null);
    setHasRun(true);
    setIsRunning(true);
    setCurrentPhase('Starting AI Investigation Engine...');

    try {
      const response = await fetch(`${API}/investigations/${investigationId}/ai/investigate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': 'trace-analyst-secret-2026',
        },
        body: JSON.stringify({
          input_text: inputText.trim(),
          auto_expand: true,
          scan_depth: scanDepth,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  handleSSEEvent(data);
                } catch (e) { /* skip malformed */ }
              }
            }
          }
        } catch (e) {
          if (e.name !== 'AbortError') {
            console.error('Stream error:', e);
          }
        } finally {
          setIsRunning(false);
          setActiveScan(null);
          if (onEntitiesUpdated) onEntitiesUpdated();
        }
      };

      processStream();
    } catch (err) {
      toast.error(`Investigation failed: ${err.message}`);
      setIsRunning(false);
    }
  };

  const handleSSEEvent = (data) => {
    const { type } = data;

    setEvents(prev => [...prev, data]);

    switch (type) {
      case 'status':
        setCurrentPhase(data.message);
        break;
      case 'scan_start':
        setActiveScan(data.scan);
        setCurrentPhase(data.description || `Running ${data.scan}...`);
        break;
      case 'scan_complete':
        setActiveScan(null);
        break;
      case 'entity_discovered':
        if (data.entity) {
          setEntities(prev => {
            const exists = prev.find(e => e.id === data.entity.id);
            return exists ? prev : [...prev, data.entity];
          });
        }
        break;
      case 'relationship_discovered':
        if (data.relationship) {
          setRelationships(prev => [...prev, data.relationship]);
        }
        break;
      case 'lead_generated':
        if (data.lead) {
          setLeads(prev => [...prev, data.lead]);
        }
        break;
      case 'complete':
        setStats(data.stats);
        setCurrentPhase('Investigation complete');
        setIsRunning(false);
        toast.success(`Investigation complete — ${data.stats?.entities_discovered || 0} entities, ${data.stats?.leads_generated || 0} leads`);
        if (onEntitiesUpdated) onEntitiesUpdated();
        break;
      case 'error':
        toast.error(data.message || 'Investigation error');
        setIsRunning(false);
        break;
      default:
        break;
    }
  };

  const EntityIcon = ({ type }) => {
    const Icon = ENTITY_ICONS[type] || ENTITY_ICONS.default;
    return <Icon className="w-3.5 h-3.5" />;
  };

  const renderEventLog = () => events.map((evt, i) => {
    const ts = evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString('en', { hour12: false }) : '';

    if (evt.type === 'status') {
      return (
        <div key={i} className="flex items-start gap-2 text-xs text-gray-500 py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-gray-400">◦ {evt.message}</span>
        </div>
      );
    }
    if (evt.type === 'scan_start') {
      const icon = SCAN_ICONS[evt.scan] || SCAN_ICONS.default;
      return (
        <div key={i} className="flex items-start gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-blue-400">{icon} {evt.description || evt.scan}</span>
        </div>
      );
    }
    if (evt.type === 'scan_complete') {
      return (
        <div key={i} className="flex items-start gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-green-400">✓ {evt.message}</span>
          {evt.entities_found > 0 && (
            <span className="text-cyan-400 ml-1">+{evt.entities_found} entities</span>
          )}
        </div>
      );
    }
    if (evt.type === 'entity_discovered') {
      const e = evt.entity;
      const color = ENTITY_COLORS[e?.entity_type] || ENTITY_COLORS.default;
      return (
        <div key={i} className="flex items-center gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-purple-400">⊕</span>
          <span className={`px-1.5 py-0.5 rounded border text-xs font-medium ${color}`}>
            {e?.entity_type}
          </span>
          <span className="text-gray-200 font-mono truncate max-w-xs">{e?.value}</span>
          <span className="text-gray-500 text-xs ml-auto shrink-0">{e?.source}</span>
        </div>
      );
    }
    if (evt.type === 'relationship_discovered') {
      return (
        <div key={i} className="flex items-center gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-yellow-400">⟷</span>
          <span className="text-gray-300">Relationship: {evt.relationship?.type}</span>
          <span className="text-gray-500 text-xs ml-auto">{(evt.relationship?.confidence * 100 || 0).toFixed(0)}%</span>
        </div>
      );
    }
    if (evt.type === 'lead_generated') {
      const l = evt.lead;
      const sevColor = SEVERITY_COLORS[l?.severity] || SEVERITY_COLORS.medium;
      return (
        <div key={i} className="flex items-center gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-orange-400">⚑</span>
          <span className={`px-1.5 py-0.5 rounded border text-xs font-medium ${sevColor}`}>
            {l?.severity}
          </span>
          <span className="text-gray-200 truncate">{l?.title}</span>
        </div>
      );
    }
    if (evt.type === 'error') {
      return (
        <div key={i} className="flex items-start gap-2 text-xs py-0.5">
          <span className="text-gray-600 font-mono shrink-0">{ts}</span>
          <span className="text-red-400">✗ {evt.message}</span>
        </div>
      );
    }
    return null;
  });

  return (
    <div className="h-full flex flex-col bg-gray-950 text-gray-100 overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">AI Investigation Engine</h2>
            <p className="text-xs text-gray-400">Gemini · BOSINT · Perplexity · Swatted (6 breach sources)</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {isRunning && (
            <div className="flex items-center gap-1.5 text-xs text-blue-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Investigating...</span>
            </div>
          )}
          {stats && (
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span className="text-cyan-400 font-medium">{stats.entities_discovered} entities</span>
              <span className="text-yellow-400 font-medium">{stats.relationships_found} links</span>
              <span className="text-orange-400 font-medium">{stats.leads_generated} leads</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Panel */}
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/30">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              ref={inputRef}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !isRunning && startInvestigation()}
              placeholder="Enter any identifier: username, email, domain, IP, phone, wallet, person name..."
              className="pl-10 bg-gray-800/60 border-gray-700 text-gray-100 placeholder:text-gray-500 focus:border-purple-500 focus:ring-purple-500/20 h-11"
              disabled={isRunning}
            />
          </div>
          <select
            value={scanDepth}
            onChange={e => setScanDepth(e.target.value)}
            disabled={isRunning}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-md px-3 focus:border-purple-500 focus:outline-none"
          >
            <option value="quick">Quick</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep</option>
          </select>
          {isRunning ? (
            <Button onClick={stopInvestigation} variant="destructive" className="gap-2 h-11 px-5">
              <StopCircle className="w-4 h-4" />
              Stop
            </Button>
          ) : (
            <Button
              onClick={startInvestigation}
              className="gap-2 h-11 px-5 bg-purple-600 hover:bg-purple-700 text-white"
              disabled={!inputText.trim()}
            >
              <Zap className="w-4 h-4" />
              Investigate
            </Button>
          )}
        </div>

        {/* Example queries */}
        {!hasRun && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-xs text-gray-500">Try:</span>
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q.value}
                onClick={() => { setInputText(q.value); inputRef.current?.focus(); }}
                className="text-xs px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
              >
                {q.icon} {q.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main content */}
      {!hasRun ? (
        /* Welcome state */
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-lg">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-600/20 border border-purple-500/20 flex items-center justify-center mx-auto mb-6">
              <Brain className="w-8 h-8 text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">AI-Powered OSINT Engine</h3>
            <p className="text-gray-400 text-sm leading-relaxed mb-6">
              Enter any identifier and the AI will automatically extract entities, scan 3,000+ platforms via BOSINT,
              check 6 breach databases via Swatted, run deep web searches via Perplexity, infer relationships,
              and generate investigation leads — all without manual work.
            </p>
            <div className="grid grid-cols-2 gap-3 text-left">
              {[
                { icon: '🔍', title: 'BOSINT Username Scan', desc: '3,000+ platform checks' },
                { icon: '💀', title: 'Swatted Breach Intel', desc: 'LeakCheck, HackCheck, LeakOSINT + 3 more' },
                { icon: '🧠', title: 'Perplexity Deep Search', desc: 'Real-time web intelligence' },
                { icon: '⚡', title: 'Gemini AI Reasoning', desc: 'Auto relationship & lead generation' },
              ].map(f => (
                <div key={f.title} className="bg-gray-900 border border-gray-800 rounded-lg p-3">
                  <div className="text-lg mb-1">{f.icon}</div>
                  <div className="text-xs font-medium text-gray-200">{f.title}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{f.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">

          {/* Live Log Panel */}
          <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-800">
            {/* Status bar */}
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-900/50 border-b border-gray-800">
              {isRunning ? (
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-xs text-gray-300 truncate">{currentPhase}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-xs text-gray-400">{currentPhase}</span>
                </div>
              )}
              {activeScan && (
                <div className="ml-auto flex items-center gap-1.5 text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {activeScan}
                </div>
              )}
            </div>

            {/* Event log */}
            <div className="flex-1 overflow-y-auto p-4 font-mono space-y-0.5 bg-gray-950/50">
              {events.length === 0 && isRunning && (
                <div className="text-xs text-gray-500 animate-pulse">Initializing...</div>
              )}
              {renderEventLog()}
              <div ref={logEndRef} />
            </div>
          </div>

          {/* Results Panel */}
          <div className="w-80 flex flex-col overflow-hidden bg-gray-900/30">

            {/* Discovered Entities */}
            <div className="flex-1 overflow-y-auto">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900/80 backdrop-blur">
                <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Entities</span>
                <span className="text-xs text-cyan-400 font-medium">{entities.length}</span>
              </div>
              <div className="p-3 space-y-1.5">
                {entities.length === 0 && isRunning && (
                  <div className="text-xs text-gray-600 text-center py-4">Scanning...</div>
                )}
                {entities.map(e => {
                  const color = ENTITY_COLORS[e.entity_type] || ENTITY_COLORS.default;
                  return (
                    <div key={e.id} className={`flex items-center gap-2 px-2.5 py-2 rounded-lg border ${color} text-xs`}>
                      <EntityIcon type={e.entity_type} />
                      <span className="truncate flex-1 font-mono text-gray-200">{e.value}</span>
                      {e.risk_score > 0.6 && (
                        <AlertTriangle className="w-3 h-3 text-red-400 shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* AI Leads */}
              {leads.length > 0 && (
                <>
                  <div className="px-4 py-3 border-y border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900/80 backdrop-blur">
                    <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">AI Leads</span>
                    <span className="text-xs text-orange-400 font-medium">{leads.length}</span>
                  </div>
                  <div className="p-3 space-y-2">
                    {leads.map((lead, i) => {
                      const sevColor = SEVERITY_COLORS[lead.severity] || SEVERITY_COLORS.medium;
                      return (
                        <div key={lead.id || i} className={`p-2.5 rounded-lg border ${sevColor} text-xs`}>
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`capitalize font-semibold`}>{lead.severity}</span>
                            <span className="text-gray-500">·</span>
                            <span className="text-gray-400">{(lead.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="text-gray-200 font-medium leading-tight">{lead.title}</div>
                          <div className="text-gray-400 mt-1 leading-relaxed line-clamp-2">{lead.description}</div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>

            {/* Stats footer */}
            {stats && (
              <div className="border-t border-gray-800 p-4 bg-gray-900/50">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Scan Summary</div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: 'Entities', value: stats.entities_discovered, color: 'text-cyan-400' },
                    { label: 'Relationships', value: stats.relationships_found, color: 'text-yellow-400' },
                    { label: 'Leads', value: stats.leads_generated, color: 'text-orange-400' },
                    { label: 'Scans Run', value: stats.scans_performed, color: 'text-purple-400' },
                  ].map(s => (
                    <div key={s.label} className="bg-gray-800/60 rounded-lg p-2.5 text-center">
                      <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
