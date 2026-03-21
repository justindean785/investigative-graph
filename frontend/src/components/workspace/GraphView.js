import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Plus, Link2, Trash2, X, Network, ArrowRight, FileBox, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { useConfirmDialog } from '@/components/ui/confirm-dialog';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';
import { ENTITY_TYPES } from '@/lib/entityTypes';
import CustomNode from '../CustomNode';

const nodeTypes = {
  custom: CustomNode,
};

const RELATIONSHIP_TYPES = [
  'owns', 'registered', 'resolves_to', 'used_on', 'interacts_with', 'linked_to', 'employed_by', 'located_at'
];

const GraphView = ({ investigationId, onNavigateToEvidence, onNavigateToEntities }) => {
  const {
    entities,
    relationships,
    addEntity,
    addRelationship,
    removeEntity,
    selectEntity,
    ui,
    updateNodePosition,
  } = useInvestigationStore();

  const [showAddEntity, setShowAddEntity] = useState(false);
  const [showAddRelationship, setShowAddRelationship] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const { confirm, dialogProps, ConfirmDialog } = useConfirmDialog();

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

  // Derive nodes from entities in the store
  const nodes = useMemo(() => {
    return entities.map((entity, index) => {
      const typeInfo = ENTITY_TYPES.find(t => t.value === entity.kind) || ENTITY_TYPES[0];
      const savedPosition = ui.graphLayout.positions[entity.id];
      const angle = (index / Math.max(entities.length, 1)) * 2 * Math.PI;
      const radius = 250;

      return {
        id: entity.id,
        type: 'custom',
        position: savedPosition || {
          x: 400 + Math.cos(angle) * radius,
          y: 300 + Math.sin(angle) * radius
        },
        data: {
          label: entity.label || entity.value,
          value: entity.value,
          type: entity.kind,
          color: typeInfo.color,
          confidence: entity.confidence,
          risk_score: entity.risk / 100,
          onClick: () => {
            setSelectedNode(entity);
            selectEntity(entity.id);
          }
        }
      };
    });
  }, [entities, ui.graphLayout.positions, selectEntity]);

  // Derive edges from relationships in the store
  const edges = useMemo(() => {
    return relationships.map(rel => ({
      id: rel.id,
      source: rel.fromId,
      target: rel.toId,
      label: rel.label || rel.relType,
      type: 'smoothstep',
      animated: true,
      style: {
        stroke: 'rgba(6, 182, 212, 0.5)',
        strokeWidth: 2
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'rgba(6, 182, 212, 0.8)',
      },
      labelStyle: {
        fill: '#94a3b8',
        fontSize: 11,
        fontFamily: 'JetBrains Mono'
      },
      labelBgStyle: {
        fill: '#0a0a0a',
        fillOpacity: 0.9,
      }
    }));
  }, [relationships]);

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(nodes);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(edges);

  // Update flow state when store changes
  React.useEffect(() => {
    setFlowNodes(nodes);
  }, [nodes, setFlowNodes]);

  React.useEffect(() => {
    setFlowEdges(edges);
  }, [edges, setFlowEdges]);

  const onNodeDragStop = useCallback((event, node) => {
    updateNodePosition(node.id, node.position);
  }, [updateNodePosition]);

  const handleAddEntity = async () => {
    if (!newEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/entities`, newEntity);
      
      // Add to local store with proper format
      addEntity({
        id: response.data.id,
        kind: newEntity.entity_type,
        value: newEntity.value,
        label: newEntity.label || newEntity.value,
        notes: '',
        tags: [],
        sources: [],
        confidence: newEntity.confidence,
        risk: newEntity.risk_score * 100,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      toast.success('Entity added');
      setShowAddEntity(false);
      setNewEntity({
        entity_type: 'person',
        value: '',
        label: '',
        confidence: 0.5,
        risk_score: 0
      });
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  const handleAddRelationship = async () => {
    if (!newRelationship.source_entity_id || !newRelationship.target_entity_id) {
      toast.error('Please select both source and target entities');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/relationships`, newRelationship);
      
      // Add to local store
      addRelationship({
        id: response.data.id,
        fromId: newRelationship.source_entity_id,
        toId: newRelationship.target_entity_id,
        relType: newRelationship.relationship_type,
        label: newRelationship.label || newRelationship.relationship_type,
        confidence: 0.5,
        sources: [],
        createdAt: new Date().toISOString(),
      });

      toast.success('Connection added');
      setShowAddRelationship(false);
      setNewRelationship({
        source_entity_id: '',
        target_entity_id: '',
        relationship_type: 'linked_to',
        label: ''
      });
    } catch (error) {
      console.error('Failed to add relationship:', error);
      toast.error('Failed to add connection');
    }
  };

  const handleDeleteEntity = (entityId) => {
    confirm({
      title: 'Delete Entity',
      description: 'Delete this entity and its connections?',
      onConfirm: async () => {
        try {
          await axios.delete(`${API}/investigations/${investigationId}/entities/${entityId}`);
          removeEntity(entityId);
          setSelectedNode(null);
          toast.success('Entity deleted');
        } catch (error) {
          toast.error('Failed to delete entity');
        }
      },
    });
  };

  // Empty state - guide users to build the investigation first
  if (entities.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8" data-testid="graph-view-empty">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-6">
            <Network className="w-10 h-10 text-primary" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            No Graph Yet
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            The investigation graph visualizes entities and their connections.
            Add evidence and extract entities to build your network map.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button 
              onClick={onNavigateToEvidence}
              className="bg-primary hover:bg-primary/90 text-white"
            >
              <FileBox className="w-4 h-4 mr-2" />
              Add Evidence First
            </Button>
            
            <Button 
              onClick={onNavigateToEntities}
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/5"
            >
              <Users className="w-4 h-4 mr-2" />
              Add Entities
            </Button>
          </div>

          <div className="mt-10 p-4 bg-white/5 rounded-sm border border-white/10">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Investigation Flow</p>
            <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
              <span className="text-primary">Evidence</span>
              <ArrowRight className="w-4 h-4" />
              <span>Entities</span>
              <ArrowRight className="w-4 h-4" />
              <span>Connections</span>
              <ArrowRight className="w-4 h-4" />
              <span className="text-white font-medium">Graph</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Few entities but no relationships - suggest linking
  if (entities.length > 0 && relationships.length === 0) {
    return (
      <div className="h-full flex flex-col" data-testid="graph-view">
        <div className="flex-1 relative">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={nodeTypes}
            fitView
            style={{ background: '#0a0a0a', width: '100%', height: '100%' }}
          >
            <Background color="rgba(255,255,255,0.03)" gap={24} size={1} />
            <Controls className="!bg-black/80 !backdrop-blur-xl !border !border-white/10 !rounded-sm" />
            
            <Panel position="top-center">
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-sm px-4 py-2 flex items-center gap-3">
                <span className="text-amber-400 text-sm">
                  {entities.length} entities found. Link them to discover relationships.
                </span>
                <Button
                  onClick={onNavigateToEntities}
                  size="sm"
                  className="bg-amber-500 hover:bg-amber-600 text-black text-xs h-7"
                >
                  <Link2 className="w-3 h-3 mr-1" />
                  Link Entities
                </Button>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full relative" data-testid="graph-view">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        fitView
        style={{ background: '#0a0a0a', width: '100%', height: '100%' }}
        defaultEdgeOptions={{
          animated: true,
        }}
      >
        <Background color="rgba(255,255,255,0.03)" gap={24} size={1} />
        <Controls className="!bg-black/80 !backdrop-blur-xl !border !border-white/10 !rounded-sm" />
        <MiniMap
          nodeColor={(node) => node.data?.color || '#06b6d4'}
          className="!bg-black/80 !backdrop-blur-xl !border !border-white/10 !rounded-sm"
          maskColor="rgba(0, 0, 0, 0.8)"
        />

        <Panel position="top-left" className="flex gap-2">
          <Dialog open={showAddEntity} onOpenChange={setShowAddEntity}>
            <DialogTrigger asChild>
              <Button
                data-testid="graph-add-entity-btn"
                className="bg-primary text-white hover:bg-primary/90 shadow-glow text-xs h-8 px-3 rounded-sm"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Add Entity
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="text-lg font-heading">Add Entity</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Entity Type</Label>
                  <Select value={newEntity.entity_type} onValueChange={(value) => setNewEntity({ ...newEntity, entity_type: value })}>
                    <SelectTrigger data-testid="entity-type-select" className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {ENTITY_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Value</Label>
                  <Input
                    data-testid="entity-value-input"
                    value={newEntity.value}
                    onChange={(e) => setNewEntity({ ...newEntity, value: e.target.value })}
                    className="mt-2 bg-black/50 border-white/10 text-white"
                    placeholder="e.g., john@example.com"
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Label (Optional)</Label>
                  <Input
                    value={newEntity.label}
                    onChange={(e) => setNewEntity({ ...newEntity, label: e.target.value })}
                    className="mt-2 bg-black/50 border-white/10 text-white"
                    placeholder="Display name"
                  />
                </div>

                <Button
                  data-testid="add-entity-submit"
                  onClick={handleAddEntity}
                  className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow"
                >
                  Add Entity
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={showAddRelationship} onOpenChange={setShowAddRelationship}>
            <DialogTrigger asChild>
              <Button
                data-testid="graph-add-connection-btn"
                variant="outline"
                className="border-white/10 text-slate-300 hover:bg-white/5 hover:text-white text-xs h-8 px-3 rounded-sm"
              >
                <Link2 className="w-3.5 h-3.5 mr-1.5" />
                Add Connection
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="text-lg font-heading">Add Connection</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Source Entity</Label>
                  <Select value={newRelationship.source_entity_id} onValueChange={(value) => setNewRelationship({ ...newRelationship, source_entity_id: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue placeholder="Select source" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {entities.map(entity => (
                        <SelectItem key={entity.id} value={entity.id}>
                          {entity.label || entity.value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Relationship Type</Label>
                  <Select value={newRelationship.relationship_type} onValueChange={(value) => setNewRelationship({ ...newRelationship, relationship_type: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {RELATIONSHIP_TYPES.map(type => (
                        <SelectItem key={type} value={type}>
                          {type.replace('_', ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Target Entity</Label>
                  <Select value={newRelationship.target_entity_id} onValueChange={(value) => setNewRelationship({ ...newRelationship, target_entity_id: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue placeholder="Select target" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {entities.map(entity => (
                        <SelectItem key={entity.id} value={entity.id}>
                          {entity.label || entity.value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  data-testid="add-connection-submit"
                  onClick={handleAddRelationship}
                  className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow"
                >
                  Add Connection
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </Panel>
      </ReactFlow>

      {/* Entity Detail Drawer */}
      {selectedNode && (
        <div className="absolute right-0 top-0 bottom-0 w-80 glass-strong border-l border-white/10 p-5 overflow-y-auto z-10">
          <div className="flex items-start justify-between mb-5">
            <h3 className="text-base font-heading font-bold text-white">Entity Details</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedNode(null);
                selectEntity(null);
              }}
              className="text-slate-400 hover:text-white h-6 w-6 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Type</p>
              <p className="text-white text-sm">{selectedNode.kind}</p>
            </div>

            <div>
              <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Value</p>
              <p className="text-white font-mono text-sm break-all">{selectedNode.value}</p>
            </div>

            {selectedNode.label && selectedNode.label !== selectedNode.value && (
              <div>
                <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Label</p>
                <p className="text-white text-sm">{selectedNode.label}</p>
              </div>
            )}

            <div>
              <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-black/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary"
                    style={{ width: `${selectedNode.confidence * 100}%` }}
                  />
                </div>
                <span className="text-white text-xs font-mono">{Math.round(selectedNode.confidence * 100)}%</span>
              </div>
            </div>

            <div>
              <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Risk Score</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-black/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500"
                    style={{ width: `${selectedNode.risk}%` }}
                  />
                </div>
                <span className="text-white text-xs font-mono">{Math.round(selectedNode.risk)}%</span>
              </div>
            </div>

            {selectedNode.notes && (
              <div>
                <p className="text-xs text-cyan-500/80 uppercase tracking-wider mb-1">Notes</p>
                <p className="text-slate-300 text-sm">{selectedNode.notes}</p>
              </div>
            )}

            <div className="pt-4 border-t border-white/10">
              <Button
                onClick={() => handleDeleteEntity(selectedNode.id)}
                className="w-full bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 rounded-sm text-xs"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                Delete Entity
              </Button>
            </div>
          </div>
        </div>
      )}
      <ConfirmDialog {...dialogProps} />
    </div>
  );
};

export default GraphView;
