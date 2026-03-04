import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import { Plus, Link2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { API } from '../App';
import CustomNode from './CustomNode';

const nodeTypes = {
  custom: CustomNode,
};

const ENTITY_TYPES = [
  { value: 'person', label: 'Person', icon: '👤', color: '#00d9ff' },
  { value: 'email', label: 'Email', icon: '📧', color: '#14f195' },
  { value: 'phone', label: 'Phone', icon: '📱', color: '#f97316' },
  { value: 'domain', label: 'Domain', icon: '🌐', color: '#00d9ff' },
  { value: 'ip', label: 'IP Address', icon: '🖥️', color: '#7c3aed' },
  { value: 'username', label: 'Username', icon: '👨‍💻', color: '#14f195' },
  { value: 'company', label: 'Company', icon: '🏢', color: '#f97316' },
  { value: 'wallet', label: 'Wallet', icon: '💰', color: '#fbbf24' },
  { value: 'social', label: 'Social Account', icon: '💬', color: '#3b82f6' },
  { value: 'url', label: 'URL', icon: '🔗', color: '#00d9ff' },
];

const RELATIONSHIP_TYPES = [
  'owns', 'registered', 'resolves_to', 'used_on', 'interacts_with', 'linked_to', 'employed_by', 'located_at'
];

const GraphTab = ({ investigationId, refreshTrigger, onRefresh }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showAddEntity, setShowAddEntity] = useState(false);
  const [showAddRelationship, setShowAddRelationship] = useState(false);
  
  const [newEntity, setNewEntity] = useState({
    entity_type: 'person',
    value: '',
    label: '',
    confidence: 0.5,
    risk_score: 0
  });

  const [newRelationship, setNewRelationship] = useState({
    source_entity_id: '',
    target_entity_id: '',
    relationship_type: 'linked_to',
    label: ''
  });

  useEffect(() => {
    fetchData();
  }, [investigationId, refreshTrigger]);

  const fetchData = async () => {
    try {
      const [entitiesRes, relationshipsRes] = await Promise.all([
        axios.get(`${API}/investigations/${investigationId}/entities`),
        axios.get(`${API}/investigations/${investigationId}/relationships`)
      ]);

      setEntities(entitiesRes.data);
      setRelationships(relationshipsRes.data);
      buildGraph(entitiesRes.data, relationshipsRes.data);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      toast.error('Failed to load graph data');
    }
  };

  const buildGraph = (entities, relationships) => {
    // Create nodes
    const newNodes = entities.map((entity, index) => {
      const typeInfo = ENTITY_TYPES.find(t => t.value === entity.entity_type) || ENTITY_TYPES[0];
      const angle = (index / entities.length) * 2 * Math.PI;
      const radius = 300;
      
      return {
        id: entity.id,
        type: 'custom',
        position: {
          x: 500 + Math.cos(angle) * radius,
          y: 400 + Math.sin(angle) * radius
        },
        data: {
          label: entity.label || entity.value,
          value: entity.value,
          type: entity.entity_type,
          icon: typeInfo.icon,
          color: typeInfo.color,
          confidence: entity.confidence,
          risk_score: entity.risk_score,
          onClick: () => setSelectedNode(entity)
        }
      };
    });

    // Create edges
    const newEdges = relationships.map(rel => ({
      id: rel.id,
      source: rel.source_entity_id,
      target: rel.target_entity_id,
      label: rel.label || rel.relationship_type,
      type: 'smoothstep',
      animated: true,
      style: {
        stroke: 'rgba(0, 217, 255, 0.5)',
        strokeWidth: 2
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'rgba(0, 217, 255, 0.8)',
      },
      labelStyle: {
        fill: '#94a3b8',
        fontSize: 12,
        fontFamily: 'JetBrains Mono'
      },
      labelBgStyle: {
        fill: '#0d1b2a',
        fillOpacity: 0.8,
      }
    }));

    setNodes(newNodes);
    setEdges(newEdges);
  };

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({
      ...params,
      type: 'smoothstep',
      animated: true,
      style: { stroke: 'rgba(0, 217, 255, 0.5)', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'rgba(0, 217, 255, 0.8)',
      }
    }, eds));
  }, [setEdges]);

  const addEntity = async () => {
    if (!newEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }

    try {
      await axios.post(`${API}/investigations/${investigationId}/entities`, newEntity);
      toast.success('Entity added successfully');
      setShowAddEntity(false);
      setNewEntity({
        entity_type: 'person',
        value: '',
        label: '',
        confidence: 0.5,
        risk_score: 0
      });
      fetchData();
      onRefresh();
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  const addRelationship = async () => {
    if (!newRelationship.source_entity_id || !newRelationship.target_entity_id) {
      toast.error('Please select both source and target entities');
      return;
    }

    try {
      await axios.post(`${API}/investigations/${investigationId}/relationships`, newRelationship);
      toast.success('Relationship added successfully');
      setShowAddRelationship(false);
      setNewRelationship({
        source_entity_id: '',
        target_entity_id: '',
        relationship_type: 'linked_to',
        label: ''
      });
      fetchData();
      onRefresh();
    } catch (error) {
      console.error('Failed to add relationship:', error);
      toast.error('Failed to add relationship');
    }
  };

  const deleteEntity = async (entityId) => {
    if (!window.confirm('Delete this entity and its relationships?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/entities/${entityId}`);
      toast.success('Entity deleted');
      setSelectedNode(null);
      fetchData();
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete entity');
    }
  };

  return (
    <div className="relative glass border border-[#00d9ff]/20 rounded-lg overflow-hidden" style={{ height: '700px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        style={{ background: '#0a1628', width: '100%', height: '100%' }}
        defaultEdgeOptions={{
          animated: true,
        }}
      >
        <Background color="#1e293b" gap={16} />
        <Controls className="bg-[#0d1b2a] border border-[#00d9ff]/20" />
        <MiniMap
          nodeColor={(node) => node.data.color || '#00d9ff'}
          className="bg-[#0d1b2a] border border-[#00d9ff]/20"
        />
        
        <Panel position="top-right" className="space-x-2">
          <Dialog open={showAddEntity} onOpenChange={setShowAddEntity}>
            <DialogTrigger asChild>
              <Button
                data-testid="add-entity-btn"
                className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] shadow-[0_0_15px_rgba(0,217,255,0.3)] font-bold uppercase text-xs"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Entity
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-xl border-[#00d9ff]/20 text-white">
              <DialogHeader>
                <DialogTitle className="text-2xl text-[#00d9ff]">Add Entity</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Entity Type</Label>
                  <Select value={newEntity.entity_type} onValueChange={(value) => setNewEntity({ ...newEntity, entity_type: value })}>
                    <SelectTrigger data-testid="entity-type-select" className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                      {ENTITY_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.icon} {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Value</Label>
                  <Input
                    data-testid="entity-value-input"
                    value={newEntity.value}
                    onChange={(e) => setNewEntity({ ...newEntity, value: e.target.value })}
                    className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white"
                    placeholder="Enter entity value"
                  />
                </div>

                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Label (Optional)</Label>
                  <Input
                    value={newEntity.label}
                    onChange={(e) => setNewEntity({ ...newEntity, label: e.target.value })}
                    className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white"
                    placeholder="Custom label"
                  />
                </div>

                <Button
                  data-testid="add-entity-submit"
                  onClick={addEntity}
                  className="w-full bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase"
                >
                  Add Entity
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={showAddRelationship} onOpenChange={setShowAddRelationship}>
            <DialogTrigger asChild>
              <Button
                data-testid="add-relationship-btn"
                className="border border-[#00d9ff]/30 text-[#00d9ff] hover:bg-[#00d9ff]/10 font-bold uppercase text-xs"
              >
                <Link2 className="w-4 h-4 mr-2" />
                Add Connection
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-xl border-[#00d9ff]/20 text-white">
              <DialogHeader>
                <DialogTitle className="text-2xl text-[#00d9ff]">Add Relationship</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Source Entity</Label>
                  <Select value={newRelationship.source_entity_id} onValueChange={(value) => setNewRelationship({ ...newRelationship, source_entity_id: value })}>
                    <SelectTrigger data-testid="relationship-source-select" className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                      <SelectValue placeholder="Select source" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                      {entities.map(entity => (
                        <SelectItem key={entity.id} value={entity.id}>
                          {entity.label || entity.value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Relationship Type</Label>
                  <Select value={newRelationship.relationship_type} onValueChange={(value) => setNewRelationship({ ...newRelationship, relationship_type: value })}>
                    <SelectTrigger className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                      {RELATIONSHIP_TYPES.map(type => (
                        <SelectItem key={type} value={type}>
                          {type.replace('_', ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Target Entity</Label>
                  <Select value={newRelationship.target_entity_id} onValueChange={(value) => setNewRelationship({ ...newRelationship, target_entity_id: value })}>
                    <SelectTrigger data-testid="relationship-target-select" className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                      <SelectValue placeholder="Select target" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                      {entities.map(entity => (
                        <SelectItem key={entity.id} value={entity.id}>
                          {entity.label || entity.value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  data-testid="add-relationship-submit"
                  onClick={addRelationship}
                  className="w-full bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase"
                >
                  Add Relationship
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </Panel>
      </ReactFlow>

      {/* Details Panel */}
      {selectedNode && (
        <div className="absolute right-4 top-4 bottom-4 w-80 glass-xl border border-[#00d9ff]/20 rounded-lg p-6 overflow-y-auto">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-bold text-[#00d9ff]">Entity Details</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedNode(null)}
              className="text-[#94a3b8] hover:text-white"
            >
              ✕
            </Button>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Type</p>
              <p className="text-white">{selectedNode.entity_type}</p>
            </div>
            
            <div>
              <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Value</p>
              <p className="text-white font-mono text-sm break-all">{selectedNode.value}</p>
            </div>

            {selectedNode.label && (
              <div>
                <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Label</p>
                <p className="text-white">{selectedNode.label}</p>
              </div>
            )}

            <div>
              <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-[#0a1628] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#00d9ff]"
                    style={{ width: `${selectedNode.confidence * 100}%` }}
                  />
                </div>
                <span className="text-white text-sm">{Math.round(selectedNode.confidence * 100)}%</span>
              </div>
            </div>

            <div>
              <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Risk Score</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-[#0a1628] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#ff3b30]"
                    style={{ width: `${selectedNode.risk_score * 100}%` }}
                  />
                </div>
                <span className="text-white text-sm">{Math.round(selectedNode.risk_score * 100)}%</span>
              </div>
            </div>

            {selectedNode.notes && (
              <div>
                <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-1">Notes</p>
                <p className="text-white text-sm">{selectedNode.notes}</p>
              </div>
            )}

            <Button
              onClick={() => deleteEntity(selectedNode.id)}
              className="w-full bg-[#ff3b30] text-white hover:bg-[#ff3b30]/80 font-bold uppercase"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Entity
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphTab;
