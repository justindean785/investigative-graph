import React, { useState } from 'react';
import {
  Globe, Wifi, Search, Hash, User, Download, Upload,
  Loader2, CheckCircle, XCircle, AlertTriangle, ExternalLink,
  Copy, ChevronDown, ChevronRight, Server, MapPin, Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';

// ─── Utility helpers ────────────────────────────────────────────────────────

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => toast.success('Copied to clipboard'));
};

const SectionHeader = ({ icon: Icon, title, color = '#14f195' }) => (
  <div className="flex items-center gap-2 mb-3">
    <Icon className="w-4 h-4" style={{ color }} />
    <h3 className="text-sm font-semibold text-white">{title}</h3>
  </div>
);

const ResultCard = ({ children, className = '' }) => (
  <div className={`bg-black/30 border border-white/10 rounded-sm p-3 text-xs font-mono text-slate-300 ${className}`}>
    {children}
  </div>
);

const KV = ({ label, value, mono = true }) => {
  if (value === null || value === undefined || value === '') return null;
  const display = Array.isArray(value) ? value.join(', ') : String(value);
  return (
    <div className="flex gap-2 py-0.5">
      <span className="text-slate-500 w-32 flex-shrink-0">{label}</span>
      <span className={`text-slate-200 break-all ${mono ? 'font-mono' : ''}`}>{display}</span>
    </div>
  );
};

// ─── DNS Lookup Tool ─────────────────────────────────────────────────────────

const DNSTool = () => {
  const [target, setTarget] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!target.trim()) return toast.error('Enter a domain or IP');
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/tools/dns-lookup`, {
        target: target.trim(),
        record_types: ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA'],
      });
      setResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'DNS lookup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={Globe} title="DNS Lookup" color="#06b6d4" />
      <div className="flex gap-2">
        <Input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="domain.com or IP address"
          className="bg-black/30 border-white/10 h-8 text-xs font-mono"
        />
        <Button onClick={run} disabled={loading} className="h-8 px-3 text-xs">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Lookup'}
        </Button>
      </div>

      {result && (
        <ResultCard>
          <div className="flex items-center justify-between mb-2">
            <span className="text-cyan-400 font-semibold">{result.target}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1 text-[10px] text-slate-500"
              onClick={() => copyToClipboard(JSON.stringify(result, null, 2))}
            >
              <Copy className="w-3 h-3 mr-1" /> Copy
            </Button>
          </div>
          {Object.entries(result.records || {}).map(([type, records]) => (
            <div key={type} className="mb-2">
              <span className="text-yellow-400 text-[10px] font-bold mr-2">{type}</span>
              {Array.isArray(records)
                ? records.map((r, i) => (
                    <div key={i} className="ml-4 text-slate-300">
                      {typeof r === 'object' ? JSON.stringify(r) : r}
                    </div>
                  ))
                : <div className="ml-4 text-slate-300">{JSON.stringify(records)}</div>}
            </div>
          ))}
          {Object.entries(result.errors || {}).map(([type, err]) => (
            <div key={type} className="text-red-400 text-[10px]">
              {type}: {err}
            </div>
          ))}
        </ResultCard>
      )}
    </div>
  );
};

// ─── IP Geolocation Tool ─────────────────────────────────────────────────────

const IPGeoTool = () => {
  const [ip, setIp] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!ip.trim()) return toast.error('Enter an IP address');
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/tools/ip-geo`, { ip: ip.trim() });
      setResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'IP lookup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={MapPin} title="IP Geolocation" color="#f97316" />
      <div className="flex gap-2">
        <Input
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="8.8.8.8"
          className="bg-black/30 border-white/10 h-8 text-xs font-mono"
        />
        <Button onClick={run} disabled={loading} className="h-8 px-3 text-xs">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Lookup'}
        </Button>
      </div>

      {result && (
        <ResultCard>
          <div className="flex flex-wrap gap-1 mb-2">
            {result.is_vpn_or_proxy && <Badge className="text-[10px] bg-red-500/20 text-red-400 border-red-500/30">VPN/Proxy</Badge>}
            {result.is_hosting && <Badge className="text-[10px] bg-orange-500/20 text-orange-400 border-orange-500/30">Hosting/DC</Badge>}
            {result.is_mobile && <Badge className="text-[10px] bg-blue-500/20 text-blue-400 border-blue-500/30">Mobile</Badge>}
          </div>
          <KV label="IP" value={result.query} />
          <KV label="Country" value={result.country ? `${result.country} (${result.countryCode})` : null} />
          <KV label="Region" value={result.regionName} />
          <KV label="City" value={result.city} />
          <KV label="ZIP" value={result.zip} />
          <KV label="Coords" value={result.lat ? `${result.lat}, ${result.lon}` : null} />
          <KV label="Timezone" value={result.timezone} />
          <KV label="ISP" value={result.isp} />
          <KV label="Org" value={result.org} />
          <KV label="ASN" value={result.as} />
          <KV label="ASN Name" value={result.asname} />
          <KV label="Reverse DNS" value={result.reverse} />
        </ResultCard>
      )}
    </div>
  );
};

// ─── WHOIS Tool ───────────────────────────────────────────────────────────────

const WHOISTool = () => {
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const run = async () => {
    if (!domain.trim()) return toast.error('Enter a domain');
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/tools/whois`, { domain: domain.trim() });
      setResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'WHOIS lookup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={Server} title="WHOIS Lookup" color="#3b82f6" />
      <div className="flex gap-2">
        <Input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="example.com"
          className="bg-black/30 border-white/10 h-8 text-xs font-mono"
        />
        <Button onClick={run} disabled={loading} className="h-8 px-3 text-xs">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Lookup'}
        </Button>
      </div>

      {result && (
        <ResultCard>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-400 font-semibold">{result.domain}</span>
            {result.privacy_protected && (
              <Badge className="text-[10px] bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                Privacy Protected
              </Badge>
            )}
          </div>
          <KV label="Registrar" value={result.registrar} />
          <KV label="Created" value={result.creation_date} />
          <KV label="Expires" value={result.expiration_date} />
          <KV label="Updated" value={result.updated_date} />
          <KV label="Name Servers" value={result.name_servers} />
          <KV label="Org" value={result.org} />
          <KV label="Country" value={result.country} />
          <KV label="DNSSEC" value={result.dnssec} />
          <KV label="Emails" value={result.emails} />

          <button
            className="mt-2 flex items-center gap-1 text-slate-500 hover:text-slate-300 text-[10px]"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Raw WHOIS data
          </button>
          {expanded && (
            <pre className="mt-1 text-[10px] text-slate-400 overflow-auto max-h-48">
              {JSON.stringify(result.raw, null, 2)}
            </pre>
          )}
        </ResultCard>
      )}
    </div>
  );
};

// ─── Username Check Tool ──────────────────────────────────────────────────────

const UsernameTool = () => {
  const [username, setUsername] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!username.trim()) return toast.error('Enter a username');
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/tools/username-check`, { username: username.trim() });
      setResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Username check failed');
    } finally {
      setLoading(false);
    }
  };

  const categoryColors = {
    developer: '#14f195',
    social: '#3b82f6',
    gaming: '#f97316',
    messaging: '#7c3aed',
    blogging: '#fbbf24',
    security: '#ef4444',
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={User} title="Username Search" color="#7c3aed" />
      <div className="flex gap-2">
        <Input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="johndoe"
          className="bg-black/30 border-white/10 h-8 text-xs font-mono"
        />
        <Button onClick={run} disabled={loading} className="h-8 px-3 text-xs">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Search'}
        </Button>
      </div>

      {result && (
        <ResultCard>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-purple-400 font-semibold">@{result.username}</span>
            <Badge className="text-[10px] bg-green-500/20 text-green-400 border-green-500/30">
              {result.found_count} / {result.total_checked} found
            </Badge>
          </div>

          {result.found.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] text-green-400 mb-1 font-semibold uppercase">Found</p>
              <div className="space-y-1">
                {result.found.map((p) => (
                  <div key={p.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-3 h-3 text-green-400" />
                      <span
                        className="text-xs"
                        style={{ color: categoryColors[p.category] || '#94a3b8' }}
                      >
                        {p.name}
                      </span>
                    </div>
                    <a
                      href={p.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-slate-300"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.not_found.length > 0 && (
            <div>
              <p className="text-[10px] text-slate-500 mb-1 font-semibold uppercase">Not found</p>
              <div className="flex flex-wrap gap-1">
                {result.not_found.map((p) => (
                  <span key={p.name} className="text-[10px] text-slate-600 bg-white/5 rounded px-1.5 py-0.5">
                    {p.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </ResultCard>
      )}
    </div>
  );
};

// ─── Hash Analyzer Tool ───────────────────────────────────────────────────────

const HashTool = () => {
  const [hashValue, setHashValue] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!hashValue.trim()) return toast.error('Enter a hash value');
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/tools/hash-identify`, { hash_value: hashValue.trim() });
      setResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Hash analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={Hash} title="Hash Analyzer" color="#ef4444" />
      <div className="flex gap-2">
        <Input
          value={hashValue}
          onChange={(e) => setHashValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="md5 / sha1 / sha256 hash"
          className="bg-black/30 border-white/10 h-8 text-xs font-mono"
        />
        <Button onClick={run} disabled={loading} className="h-8 px-3 text-xs">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Analyze'}
        </Button>
      </div>

      {result && (
        <ResultCard>
          <div className="flex items-center gap-2 mb-2">
            <Hash className="w-3 h-3 text-red-400" />
            <span className="text-red-400 font-semibold">{result.primary_type}</span>
            <Badge className="text-[10px] bg-slate-500/20 text-slate-300 border-slate-500/30">
              {result.length} chars
            </Badge>
          </div>
          <div className="text-slate-400 break-all mb-2">{result.hash}</div>
          {result.possible_types.length > 1 && (
            <div className="mb-2">
              <span className="text-slate-500 text-[10px]">Also matches: </span>
              <span className="text-slate-300 text-[10px]">{result.possible_types.slice(1).join(', ')}</span>
            </div>
          )}
          {result.threat_intel_note && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded p-2 mb-2">
              <AlertTriangle className="w-3 h-3 text-yellow-400 inline mr-1" />
              <span className="text-yellow-300 text-[10px]">{result.threat_intel_note}</span>
            </div>
          )}
          <div className="space-y-1">
            <p className="text-[10px] text-slate-500 font-semibold uppercase">Lookup Links</p>
            {Object.entries(result.lookup_urls).map(([name, url]) => (
              <a
                key={name}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300"
              >
                <ExternalLink className="w-2.5 h-2.5" />
                {name.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </a>
            ))}
          </div>
        </ResultCard>
      )}
    </div>
  );
};

// ─── Export / Import Panel ────────────────────────────────────────────────────

const ExportImportPanel = ({ investigationId, onImportSuccess }) => {
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await axios.get(`${API}/investigations/${investigationId}/export`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = res.data.investigation?.case_id
        ? `investigation_${res.data.investigation.case_id}.json`
        : 'investigation_export.json';
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Investigation exported successfully');
    } catch (e) {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const res = await axios.post(`${API}/investigations/import`, { data });
      toast.success(`Imported as ${res.data.new_case_id}`);
      if (onImportSuccess) onImportSuccess(res.data.new_investigation_id);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Import failed – check the file format');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  return (
    <div className="space-y-3">
      <SectionHeader icon={Download} title="Export / Import" color="#fbbf24" />
      <div className="flex flex-col gap-2">
        <Button
          onClick={handleExport}
          disabled={exporting}
          variant="outline"
          className="h-8 text-xs border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 justify-start gap-2"
        >
          {exporting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3 text-yellow-400" />}
          Export investigation as JSON
        </Button>

        <label className="cursor-pointer">
          <div className="flex items-center gap-2 h-8 px-3 text-xs border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 rounded-sm transition-colors">
            {importing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3 text-green-400" />}
            Import investigation from JSON
          </div>
          <input
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImport}
            disabled={importing}
          />
        </label>
      </div>
      <p className="text-[10px] text-slate-600">
        Export creates a complete bundle including entities, relationships, evidence and leads.
        Import creates a new investigation with reassigned IDs.
      </p>
    </div>
  );
};

// ─── Main Toolkit Component ───────────────────────────────────────────────────

const TOOLS = [
  { id: 'dns', label: 'DNS Lookup', icon: Globe, color: '#06b6d4', description: 'Query A, MX, NS, TXT records' },
  { id: 'ipgeo', label: 'IP Geolocation', icon: MapPin, color: '#f97316', description: 'Geolocate an IP address' },
  { id: 'whois', label: 'WHOIS', icon: Server, color: '#3b82f6', description: 'Domain registration data' },
  { id: 'username', label: 'Username Search', icon: User, color: '#7c3aed', description: 'Find profiles across platforms' },
  { id: 'hash', label: 'Hash Analyzer', icon: Hash, color: '#ef4444', description: 'Identify hash type & lookup links' },
  { id: 'export', label: 'Export / Import', icon: Download, color: '#fbbf24', description: 'Save or load investigation data' },
];

const OsintToolkitWorkspace = ({ investigationId, onNavigateToEvidence }) => {
  const [activeTool, setActiveTool] = useState('dns');

  const renderTool = () => {
    switch (activeTool) {
      case 'dns':
        return <DNSTool />;
      case 'ipgeo':
        return <IPGeoTool />;
      case 'whois':
        return <WHOISTool />;
      case 'username':
        return <UsernameTool />;
      case 'hash':
        return <HashTool />;
      case 'export':
        return <ExportImportPanel investigationId={investigationId} />;
      default:
        return null;
    }
  };

  const currentTool = TOOLS.find((t) => t.id === activeTool);

  return (
    <div className="h-full flex overflow-hidden">
      {/* Tool Selector Sidebar */}
      <div className="w-48 border-r border-white/5 bg-black/20 flex flex-col py-3 gap-0.5 flex-shrink-0">
        <div className="px-3 mb-2">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-primary" />
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">OSINT Toolkit</span>
          </div>
        </div>

        {TOOLS.map((tool) => {
          const ToolIcon = tool.icon;
          const isActive = activeTool === tool.id;
          return (
            <button
              key={tool.id}
              onClick={() => setActiveTool(tool.id)}
              className={`mx-2 px-2 py-2 rounded-sm flex items-start gap-2.5 text-left transition-all ${
                isActive ? 'bg-white/10' : 'hover:bg-white/5'
              }`}
            >
              {isActive && (
                <div
                  className="absolute left-0 w-0.5 h-8 rounded-r"
                  style={{ backgroundColor: tool.color }}
                />
              )}
              <ToolIcon
                className="w-3.5 h-3.5 mt-0.5 flex-shrink-0"
                style={{ color: isActive ? tool.color : '#64748b' }}
              />
              <div>
                <div className={`text-xs font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}>
                  {tool.label}
                </div>
                <div className="text-[10px] text-slate-600 leading-tight">{tool.description}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Tool Content */}
      <div className="flex-1 overflow-y-auto p-5">
        <div className="max-w-2xl mx-auto">
          {/* Tool Header */}
          {currentTool && (
            <div className="flex items-center gap-2 mb-5 pb-3 border-b border-white/5">
              <div
                className="w-7 h-7 rounded-sm flex items-center justify-center"
                style={{ backgroundColor: `${currentTool.color}20`, border: `1px solid ${currentTool.color}40` }}
              >
                <currentTool.icon className="w-4 h-4" style={{ color: currentTool.color }} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">{currentTool.label}</h2>
                <p className="text-[10px] text-slate-500">{currentTool.description}</p>
              </div>
            </div>
          )}

          {renderTool()}
        </div>
      </div>
    </div>
  );
};

export default OsintToolkitWorkspace;
