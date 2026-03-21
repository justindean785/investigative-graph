import React, { useState, useCallback, useEffect } from 'react';
import { FileText, Shield, AlertTriangle, Download, Loader2, Users, Link2, Eye, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';

const THREAT_COLORS = {
  CRITICAL: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-500' },
  HIGH: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', dot: 'bg-orange-500' },
  MEDIUM: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  LOW: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', dot: 'bg-green-500' },
};

const ReportView = ({ investigationId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateReport = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/investigations/${investigationId}/report`);
      setReport(res.data);
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    generateReport();
  }, [generateReport]);

  const handleExport = async (format) => {
    try {
      const res = await axios.get(`${API}/investigations/${investigationId}/export/${format}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `investigation-${investigationId}.${format === 'json' ? 'json' : format === 'csv' ? 'zip' : 'md'}`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(`Export failed: ${format}`);
    }
  };

  if (loading && !report) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-primary animate-spin" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <FileText className="w-12 h-12 text-slate-600 mb-4" />
        <p className="text-sm text-slate-400">No report data available</p>
        <Button onClick={generateReport} className="mt-4" size="sm">Generate Report</Button>
      </div>
    );
  }

  const { threat_assessment, statistics, key_findings, leads } = report;
  const tc = THREAT_COLORS[threat_assessment?.threat_level] || THREAT_COLORS.LOW;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-heading font-bold text-white">Investigation Report</h2>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleExport('json')} title="Export JSON">
            <Download className="w-3.5 h-3.5 mr-1" /> JSON
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleExport('csv')} title="Export CSV">
            <Download className="w-3.5 h-3.5 mr-1" /> CSV
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleExport('markdown')} title="Export Markdown">
            <Download className="w-3.5 h-3.5 mr-1" /> MD
          </Button>
        </div>
      </div>

      {/* Threat Assessment Card */}
      <div className={`rounded-sm border ${tc.border} ${tc.bg} p-4`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className={`w-5 h-5 ${tc.text}`} />
            <span className={`text-sm font-bold uppercase tracking-wider ${tc.text}`}>
              {threat_assessment.threat_level} Threat
            </span>
          </div>
          <span className={`text-2xl font-mono font-bold ${tc.text}`}>
            {(threat_assessment.overall_score * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
          <div className={`h-full ${tc.dot} rounded-full transition-all`} style={{ width: `${threat_assessment.overall_score * 100}%` }} />
        </div>
        <div className="mt-3 flex gap-4 text-xs text-slate-400">
          <span>Density: {threat_assessment.connection_density}</span>
          <span>High-risk entities: {threat_assessment.high_risk_entities?.length || 0}</span>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: 'Entities', value: statistics.total_entities, icon: Users, color: 'text-emerald-400' },
          { label: 'Connections', value: statistics.total_relationships, icon: Link2, color: 'text-blue-400' },
          { label: 'Evidence', value: statistics.total_evidence, icon: Eye, color: 'text-amber-400' },
          { label: 'Verified', value: statistics.verified_evidence, icon: Shield, color: 'text-green-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white/[0.02] border border-white/5 rounded-sm p-3">
            <div className="flex items-center gap-2">
              <Icon className={`w-4 h-4 ${color}`} />
              <span className="text-xs text-slate-500">{label}</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">{value}</span>
          </div>
        ))}
      </div>

      {/* Entity Breakdown */}
      {statistics.entity_breakdown && Object.keys(statistics.entity_breakdown).length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-sm p-4">
          <h3 className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-3">Entity Breakdown</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(statistics.entity_breakdown).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
              <Badge key={type} variant="secondary" className="bg-white/5 text-slate-300 border-0 text-xs">
                {type}: {count}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Key Findings */}
      {key_findings && key_findings.length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-sm p-4">
          <h3 className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-3">
            <TrendingUp className="w-3.5 h-3.5 inline mr-1" />
            Key Findings — Most Connected Entities
          </h3>
          <div className="space-y-2">
            {key_findings.slice(0, 5).map((f, i) => (
              <div key={f.entity_id} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-600 font-mono w-5">{i + 1}.</span>
                  <div>
                    <span className="text-sm text-white font-mono">{f.value}</span>
                    <Badge variant="secondary" className="ml-2 bg-white/5 text-slate-400 border-0 text-[10px]">{f.type}</Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-slate-400">{f.connections} connections</span>
                  {f.risk_score >= 0.7 && (
                    <Badge className="bg-red-500/10 text-red-400 border-red-500/30 text-[10px]">HIGH RISK</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Leads */}
      {leads && leads.length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-sm p-4">
          <h3 className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-3">Active Leads</h3>
          <div className="space-y-2">
            {leads.filter(l => l.status !== 'dismissed').slice(0, 8).map(l => {
              const sc = THREAT_COLORS[l.severity?.toUpperCase()] || THREAT_COLORS.MEDIUM;
              return (
                <div key={l.id} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                    <span className="text-sm text-white">{l.title}</span>
                  </div>
                  <Badge variant="secondary" className="bg-white/5 text-slate-400 border-0 text-[10px]">{l.status}</Badge>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* High Risk Entities */}
      {threat_assessment.high_risk_entities?.length > 0 && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-sm p-4">
          <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">
            <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />
            High Risk Entities
          </h3>
          <div className="space-y-1.5">
            {threat_assessment.high_risk_entities.map(e => (
              <div key={e.id} className="flex items-center justify-between text-sm">
                <span className="text-white font-mono">{e.value}</span>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-white/5 text-slate-400 border-0 text-[10px]">{e.type}</Badge>
                  <span className="text-red-400 font-mono text-xs">{(e.risk_score * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10px] text-slate-600 text-right pt-2">
        Generated: {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
};

export default ReportView;
