import React from 'react';
import { Handle, Position } from 'reactflow';
import { Network } from 'lucide-react';
import { ENTITY_KIND_ICONS } from '@/lib/entityTypes';

function riskColor(score) {
  if (score >= 0.75) return '#ef4444';
  if (score >= 0.5) return '#f97316';
  if (score >= 0.25) return '#eab308';
  return null;
}

const CustomNode = ({ data }) => {
  const Icon = ENTITY_KIND_ICONS[data.type] || Network;
  const accent = data.color || '#06b6d4';
  const risk = data.risk_score || 0;
  const rc = riskColor(risk);
  const borderColor = rc || `${accent}99`;
  const glowColor = rc ? `${rc}55` : `${accent}33`;

  return (
    <div
      onClick={data.onClick}
      className="relative cursor-pointer group"
      data-testid={`node-${data.value}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary !border-2 !border-[#0a0a0a]" />

      <div
        className="min-w-[4.5rem] bg-black/80 backdrop-blur-xl border-2 rounded-sm w-20 h-20 flex items-center justify-center shadow-xl transition-transform duration-300 group-hover:scale-105"
        style={{
          borderColor,
          boxShadow: `0 0 16px ${glowColor}`,
        }}
      >
        <Icon className="w-9 h-9" style={{ color: rc || accent }} strokeWidth={1.5} aria-hidden />
      </div>

      {/* Label */}
      <div
        className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-black/80 backdrop-blur-xl px-3 py-1 rounded-sm text-xs font-medium border border-white/10 text-slate-200"
        style={{ borderColor: `${accent}40` }}
      >
        <p className="max-w-[12rem] truncate">{data.label}</p>
      </div>

      {/* Risk badge */}
      {risk >= 0.5 && (
        <div
          className="absolute -top-2 -right-2 w-7 h-7 rounded-sm flex items-center justify-center text-white text-[10px] font-bold border-2 border-[#0a0a0a] font-mono"
          style={{ backgroundColor: rc }}
          title={`Risk: ${(risk * 100).toFixed(0)}%`}
        >
          {(risk * 100).toFixed(0)}
        </div>
      )}

      {/* Confidence bar (bottom-left) */}
      {data.confidence != null && data.confidence > 0 && (
        <div className="absolute -bottom-1 -left-1 w-5 h-1.5 bg-black/60 rounded-full overflow-hidden border border-white/10" title={`Confidence: ${(data.confidence * 100).toFixed(0)}%`}>
          <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${data.confidence * 100}%` }} />
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-primary !border-2 !border-[#0a0a0a]" />
    </div>
  );
};

export default CustomNode;
