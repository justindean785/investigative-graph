import React from 'react';
import { Handle, Position } from 'reactflow';
import { 
  User, Mail, Phone, Globe, Server, AtSign, Building2, 
  Wallet, MessageSquare, Link, Hash, AlertTriangle, MapPin
} from 'lucide-react';

const ICON_MAP = {
  person: User,
  email: Mail,
  phone: Phone,
  domain: Globe,
  ip: Server,
  username: AtSign,
  company: Building2,
  wallet: Wallet,
  social: MessageSquare,
  url: Link,
  hash: Hash,
  location: MapPin,
};

const RISK_THRESHOLD = 0.5;

const CustomNode = ({ data, selected }) => {
  const IconComponent = ICON_MAP[data.type] || MapPin;
  const isHighRisk = data.risk_score > RISK_THRESHOLD;
  const nodeColor = data.color || '#06b6d4';

  return (
    <div
      onClick={data.onClick}
      className="relative cursor-pointer group"
      data-testid={`node-${data.value}`}
      style={{ minWidth: 160 }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !border !border-white/30"
        style={{ background: nodeColor, top: -4 }}
      />

      {/* Main card */}
      <div
        className="relative flex items-center gap-2.5 px-3 py-2.5 rounded-sm border backdrop-blur-xl transition-shadow"
        style={{
          background: 'rgba(10, 10, 12, 0.9)',
          borderColor: selected ? nodeColor : isHighRisk ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.12)',
          boxShadow: selected
            ? `0 0 18px ${nodeColor}50, 0 0 6px ${nodeColor}30`
            : isHighRisk
            ? '0 0 12px rgba(239,68,68,0.2)'
            : '0 4px 12px rgba(0,0,0,0.6)',
        }}
      >
        {/* Icon badge */}
        <div
          className="flex-shrink-0 w-7 h-7 rounded-sm flex items-center justify-center"
          style={{ background: `${nodeColor}18`, border: `1px solid ${nodeColor}40` }}
        >
          <IconComponent className="w-3.5 h-3.5" style={{ color: nodeColor }} />
        </div>

        {/* Text content */}
        <div className="flex-1 min-w-0">
          <p
            className="text-[11px] font-medium truncate leading-tight"
            style={{ color: selected ? nodeColor : '#f1f5f9' }}
          >
            {data.label || data.value}
          </p>
          <p className="text-[9px] font-mono uppercase tracking-wider mt-0.5" style={{ color: `${nodeColor}90` }}>
            {data.type}
          </p>
        </div>

        {/* Risk indicator */}
        {isHighRisk && (
          <div
            className="flex-shrink-0 w-4 h-4 rounded-sm flex items-center justify-center"
            style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)' }}
          >
            <AlertTriangle className="w-2.5 h-2.5 text-red-400" />
          </div>
        )}
      </div>

      {/* Selected glow accent line */}
      {selected && (
        <div
          className="absolute -bottom-px left-2 right-2 h-px rounded-full"
          style={{ background: `linear-gradient(90deg, transparent, ${nodeColor}, transparent)` }}
        />
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !border !border-white/30"
        style={{ background: nodeColor, bottom: -4 }}
      />
    </div>
  );
};

export default CustomNode;
