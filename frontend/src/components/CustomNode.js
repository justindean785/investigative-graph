import React from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data }) => {
  return (
    <div
      onClick={data.onClick}
      className="relative cursor-pointer group"
      data-testid={`node-${data.value}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#00d9ff] !border-2 !border-[#0a1628]" />
      
      <div
        className="bg-[#112240] border-2 rounded-full w-20 h-20 flex items-center justify-center transition-all duration-300 group-hover:scale-110"
        style={{
          borderColor: data.color || '#00d9ff',
          boxShadow: `0 0 10px ${data.color || '#00d9ff'}40`
        }}
      >
        <div className="text-center">
          <div className="text-3xl">{data.icon || '📍'}</div>
        </div>
      </div>

      <div
        className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-[#0d1b2a]/90 backdrop-blur-sm px-3 py-1 rounded text-xs font-medium border"
        style={{ borderColor: `${data.color || '#00d9ff'}40` }}
      >
        <p className="text-white">{data.label}</p>
      </div>

      {data.risk_score > 0.5 && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-[#ff3b30] rounded-full flex items-center justify-center text-white text-xs font-bold border-2 border-[#0a1628]">
          !
        </div>
      )}
      
      <Handle type="source" position={Position.Bottom} className="!bg-[#00d9ff] !border-2 !border-[#0a1628]" />
    </div>
  );
};

export default CustomNode;
