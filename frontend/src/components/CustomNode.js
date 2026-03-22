import React from 'react';
import { Handle, Position } from 'reactflow';
import { Globe, Mail, Phone, User, Hash, Link2, Wallet, Server } from 'lucide-react';

const TYPE_ICON = {
  domain: Globe,
  email: Mail,
  phone: Phone,
  username: User,
  person: User,
  ip: Server,
  url: Link2,
  wallet: Wallet,
  hash: Hash,
};

const CustomNode = ({ data }) => {
  const Icon = TYPE_ICON[data.kind] || TYPE_ICON[data.type] || Globe;
  const accent = data.color || '#06b6d4';
  return (
    <div
      onClick={data.onClick}
      className="relative cursor-pointer group"
      data-testid={`node-${data.value}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#00d9ff] !border-2 !border-[#0a1628]" />
      
      <div
        className="bg-black/60 border rounded-sm w-20 h-20 flex items-center justify-center transition-transform duration-200 group-hover:scale-[1.06]"
        style={{
          borderColor: `${accent}66`,
          boxShadow: `0 0 16px ${accent}26`
        }}
      >
        <div className="text-center">
          <Icon className="w-7 h-7" style={{ color: accent }} />
        </div>
      </div>

      <div
        className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-black/80 backdrop-blur-sm px-3 py-1 rounded-sm text-xs font-medium border"
        style={{ borderColor: `${accent}40` }}
      >
        <p className="text-white">{data.label}</p>
      </div>

      {data.risk_score > 0.5 && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-sm flex items-center justify-center text-white text-xs font-bold border border-black/50">
          !
        </div>
      )}
      
      <Handle type="source" position={Position.Bottom} className="!bg-[#00d9ff] !border-2 !border-[#0a1628]" />
    </div>
  );
};

export default CustomNode;
