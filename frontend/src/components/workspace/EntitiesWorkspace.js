import React, { useState, useMemo } from 'react';
import { Users, Plus, Link2, Trash2, ChevronRight, Search, ArrowRight, Network, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { useConfirmDialog } from '@/components/ui/confirm-dialog';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';
import { ENTITY_TYPES, EntityKindIcon } from '@/lib/entityTypes';

const RELATIONSHIP_TYPES = [
  { value: 'owns', label: 'Owns' },
  { value: 'registered', label: 'Registered' },
  { value: 'resolves_to', label: 'Resolves to' },
  { value: 'used_on', label: 'Used on' },
  { value: 'interacts_with', label: 'Interacts with' },
  { value: 'linked_to', label: 'Linked to' },
  { value: 'employed_by', label: 'Employed by' },
  { value: 'located_at', label: 'Located at' },
  { value: 'transferred_to', label: 'Transferred to' },
  { value: 'associated_with', label: 'Associated with' },
];

const EntitiesWorkspace = ({ investigationId, onNavigateToGraph, onNavigateToEvidence }) => {
  const { entities, relationships, addEntity, addRelationship, removeEntity, updateEntity } = useInvestigationStore();
  const { confirm, dialogProps, ConfirmDialog } = useConfirmDialog();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingEntity, setEditingEntity] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [expandedEntity, setExpandedEntity] = useState(null);

  const [newEntity, setNewEntity] = useState({
    entity_type: 'person',
    value: '',
    label: '',
    notes: '',
    confidence: 0.5,
  });

  const [editEntity, setEditEntity] = useState({
    value: '',
    label: '',
    notes: '',
    confidence: 0.5,
  });

  const [newLink, setNewLink] = useState({
    source_entity_id: '',
    target_entity_id: '',
    relationship_type: 'linked_to',
  });

  const getTypeInfo = (type) => ENTITY_TYPES.find(t => t.value === type) || ENTITY_TYPES[0];

  const getEntityConnections = (entityId) => {
    return relationships.filter(r => r.fromId === entityId || r.toId === entityId);
  };

  const filteredEntities = useMemo(() => entities.filter(entity =>
    entity.value.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (entity.label && entity.label.toLowerCase().includes(searchQuery.toLowerCase())) ||
    entity.kind.toLowerCase().includes(searchQuery.toLowerCase())
  ), [entities, searchQuery]);

  const handleAddEntity = async () => {
    if (!newEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/entities`, newEntity);
      
      addEntity({
        id: response.data.id,
        kind: newEntity.entity_type,
        value: newEntity.value,
        label: newEntity.label || newEntity.value,
        notes: newEntity.notes,
        tags: [],
        sources: [],
        confidence: newEntity.confidence,
        risk: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      toast.success('Entity added');
      setShowAddDialog(false);
      setNewEntity({
        entity_type: 'person',
        value: '',
        label: '',
        notes: '',
        confidence: 0.5,
      });
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  const handleCreateLink = async () => {
    if (!newLink.source_entity_id || !newLink.target_entity_id) {
      toast.error('Please select both entities');
      return;
    }

    if (newLink.source_entity_id === newLink.target_entity_id) {
      toast.error('Cannot link an entity to itself');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/relationships`, newLink);
      
      addRelationship({
        id: response.data.id,
        fromId: newLink.source_entity_id,
        toId: newLink.target_entity_id,
        relType: newLink.relationship_type,
        label: newLink.relationship_type,
        confidence: 0.5,
        sources: [],
        createdAt: new Date().toISOString(),
      });

      toast.success('Connection created');
      setShowLinkDialog(false);
      setNewLink({
        source_entity_id: '',
        target_entity_id: '',
        relationship_type: 'linked_to',
      });
    } catch (error) {
      console.error('Failed to create link:', error);
      toast.error('Failed to create connection');
    }
  };

  const handleDeleteEntity = (entityId, e) => {
    e.stopPropagation();
    confirm({
      title: 'Delete Entity',
      description: 'Delete this entity and its connections?',
      onConfirm: async () => {
        try {
          await axios.delete(`${API}/investigations/${investigationId}/entities/${entityId}`);
          removeEntity(entityId);
          toast.success('Entity deleted');
        } catch (error) {
          toast.error('Failed to delete entity');
        }
      },
    });
  };

  const handleOpenEditDialog = (entity, e) => {
    e.stopPropagation();
    setEditingEntity(entity);
    setEditEntity({
      value: entity.value || '',
      label: entity.label || '',
      notes: entity.notes || '',
      confidence: entity.confidence || 0.5,
    });
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingEntity) return;
    if (!editEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }
    try {
      const payload = {
        value: editEntity.value.trim(),
        label: editEntity.label.trim() || undefined,
        notes: editEntity.notes,
        confidence: editEntity.confidence,
      };
      await axios.patch(
        `${API}/investigations/${investigationId}/entities/${editingEntity.id}`,
        payload
      );
      // Update local store so UI reflects changes immediately
      updateEntity(editingEntity.id, {
        value: payload.value,
        label: payload.label || payload.value,
        notes: payload.notes,
        confidence: payload.confidence,
      });
      toast.success('Entity updated');
      setShowEditDialog(false);
      setEditingEntity(null);
    } catch (error) {
      console.error('Failed to update entity:', error);
      toast.error('Failed to update entity');
    }
  };

  // Empty state - guide to evidence first
  if (entities.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
            <Users className="w-10 h-10 text-emerald-400" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            No Entities Yet
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            Entities are the building blocks of your investigation - people, emails, domains, wallets, and more.
            Start by adding evidence and extracting entities, or add them manually.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button 
              onClick={onNavigateToEvidence}
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/5"
            >
              <ArrowRight className="w-4 h-4 mr-2 rotate-180" />
              Start with Evidence
            </Button>
            
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button 
                  data-testid="add-first-entity-btn"
                  className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-sm"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Entity Manually
                </Button>
              </DialogTrigger>
              <DialogContent className="glass-strong border-white/10 text-white max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-xl font-heading">Add Entity</DialogTitle>
                </DialogHeader>
                <EntityForm 
                  newEntity={newEntity} 
                  setNewEntity={setNewEntity} 
                  onSubmit={handleAddEntity}
                />
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-heading font-bold text-white">Entities</h2>
          <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-0">
            {entities.length}
          </Badge>
          {relationships.length > 0 && (
            <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
              {relationships.length} connections
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {relationships.length > 0 && (
            <Button
              onClick={onNavigateToGraph}
              variant="outline"
              className="border-primary/30 text-primary hover:bg-primary/10 text-xs h-8"
            >
              <Network className="w-3.5 h-3.5 mr-1.5" />
              View Graph
            </Button>
          )}

          <Dialog open={showLinkDialog} onOpenChange={setShowLinkDialog}>
            <DialogTrigger asChild>
              <Button 
                variant="outline"
                className="border-white/10 text-slate-300 hover:bg-white/5 text-xs h-8"
                disabled={entities.length < 2}
              >
                <Link2 className="w-3.5 h-3.5 mr-1.5" />
                Link Entities
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Create Connection</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Source Entity</Label>
                  <Select value={newLink.source_entity_id} onValueChange={(value) => setNewLink({ ...newLink, source_entity_id: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue placeholder="Select entity" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {entities.map(entity => {
                        const typeInfo = getTypeInfo(entity.kind);
                        return (
                          <SelectItem key={entity.id} value={entity.id}>
                            <span className="flex items-center gap-2">
                              <EntityKindIcon kind={entity.kind} className="w-4 h-4 shrink-0" style={{ color: typeInfo.color }} />
                              <span>{entity.label || entity.value}</span>
                            </span>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex justify-center">
                  <div className="flex items-center gap-2 text-slate-500">
                    <div className="w-8 h-px bg-white/10"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="w-8 h-px bg-white/10"></div>
                  </div>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Relationship</Label>
                  <Select value={newLink.relationship_type} onValueChange={(value) => setNewLink({ ...newLink, relationship_type: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {RELATIONSHIP_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex justify-center">
                  <div className="flex items-center gap-2 text-slate-500">
                    <div className="w-8 h-px bg-white/10"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="w-8 h-px bg-white/10"></div>
                  </div>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Target Entity</Label>
                  <Select value={newLink.target_entity_id} onValueChange={(value) => setNewLink({ ...newLink, target_entity_id: value })}>
                    <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                      <SelectValue placeholder="Select entity" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                      {entities.map(entity => {
                        const typeInfo = getTypeInfo(entity.kind);
                        return (
                          <SelectItem key={entity.id} value={entity.id}>
                            <span className="flex items-center gap-2">
                              <EntityKindIcon kind={entity.kind} className="w-4 h-4 shrink-0" style={{ color: typeInfo.color }} />
                              <span>{entity.label || entity.value}</span>
                            </span>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  onClick={handleCreateLink}
                  className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm"
                >
                  <Link2 className="w-4 h-4 mr-2" />
                  Create Connection
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-entity-btn"
                className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs h-8 rounded-sm"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Add Entity
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Add Entity</DialogTitle>
              </DialogHeader>
              <EntityForm 
                newEntity={newEntity} 
                setNewEntity={setNewEntity} 
                onSubmit={handleAddEntity}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-white/5">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-black/30 border-white/10 h-9 text-sm"
            placeholder="Search entities..."
          />
        </div>
      </div>

      {/* Entity List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredEntities.map(entity => {
            const typeInfo = getTypeInfo(entity.kind);
            const connections = getEntityConnections(entity.id);
            const isExpanded = expandedEntity === entity.id;

            return (
              <div 
                key={entity.id}
                data-testid={`entity-card-${entity.id}`}
                className={`bg-black/40 border rounded-sm overflow-hidden transition-colors duration-200 cursor-pointer ${
                  isExpanded ? 'border-primary/50' : 'border-white/10 hover:border-white/20'
                }`}
                onClick={() => setExpandedEntity(isExpanded ? null : entity.id)}
              >
                <div className="p-4">
                  <div className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: `${typeInfo.color}15`, border: `1px solid ${typeInfo.color}30` }}
                    >
                      <EntityKindIcon kind={entity.kind} className="w-5 h-5" style={{ color: typeInfo.color }} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-white font-medium truncate">
                        {entity.label || entity.value}
                      </h3>
                      {entity.label && entity.label !== entity.value && (
                        <p className="text-xs text-slate-500 font-mono truncate">{entity.value}</p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <Badge className="bg-white/5 text-slate-400 border-0 text-[10px]">
                          {typeInfo.label}
                        </Badge>
                        {connections.length > 0 && (
                          <Badge className="bg-primary/10 text-primary border-0 text-[10px]">
                            {connections.length} links
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 flex-shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleOpenEditDialog(entity, e)}
                        className="h-7 w-7 p-0 text-slate-500 hover:text-cyan-400"
                        title="Edit entity"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteEntity(entity.id, e)}
                        className="h-7 w-7 p-0 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Expanded - Show connections */}
                {isExpanded && connections.length > 0 && (
                  <div className="px-4 pb-4 border-t border-white/5 bg-white/[0.02]">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mt-3 mb-2">Connections</div>
                    <div className="space-y-1">
                      {connections.map(conn => {
                        const isSource = conn.fromId === entity.id;
                        const connectedId = isSource ? conn.toId : conn.fromId;
                        const connectedEntity = entities.find(e => e.id === connectedId);
                        const connectedTypeInfo = connectedEntity ? getTypeInfo(connectedEntity.kind) : null;

                        return (
                          <div key={conn.id} className="flex items-center gap-2 text-sm">
                            <ArrowRight className={`w-3 h-3 text-slate-500 ${isSource ? '' : 'rotate-180'}`} />
                            <span className="text-slate-400">{conn.relType.replace('_', ' ')}</span>
                            {connectedEntity && (
                              <span className="text-white inline-flex items-center gap-1.5">
                                <EntityKindIcon kind={connectedEntity.kind} className="w-3.5 h-3.5 shrink-0" style={{ color: connectedTypeInfo?.color }} />
                                {connectedEntity.label || connectedEntity.value}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Edit Entity Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="glass-strong border-white/10 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-heading">Edit Entity</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Value</Label>
              <Input
                value={editEntity.value}
                onChange={(e) => setEditEntity({ ...editEntity, value: e.target.value })}
                className="mt-2 bg-black/50 border-white/10 text-white"
                placeholder="e.g., john@example.com"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Label (Optional)</Label>
              <Input
                value={editEntity.label}
                onChange={(e) => setEditEntity({ ...editEntity, label: e.target.value })}
                className="mt-2 bg-black/50 border-white/10 text-white"
                placeholder="Display name"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Confidence</Label>
              <div className="flex items-center gap-3 mt-2">
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={editEntity.confidence}
                  onChange={(e) => setEditEntity({ ...editEntity, confidence: parseFloat(e.target.value) })}
                  className="flex-1"
                />
                <span className="text-white text-sm w-12 text-right">
                  {Math.round(editEntity.confidence * 100)}%
                </span>
              </div>
            </div>
            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Notes</Label>
              <textarea
                value={editEntity.notes}
                onChange={(e) => setEditEntity({ ...editEntity, notes: e.target.value })}
                className="mt-2 w-full bg-black/50 border border-white/10 text-white rounded-sm px-3 py-2 min-h-[60px] text-sm"
                placeholder="Additional notes"
              />
            </div>
            <Button onClick={handleSaveEdit} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-sm">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
    <ConfirmDialog {...dialogProps} />
    </>
  );
};

// Entity Form Component
const EntityForm = ({ newEntity, setNewEntity, onSubmit }) => (
  <div className="space-y-4 mt-4">
    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Entity Type</Label>
      <Select value={newEntity.entity_type} onValueChange={(value) => setNewEntity({ ...newEntity, entity_type: value })}>
        <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
          {ENTITY_TYPES.map(type => (
            <SelectItem key={type.value} value={type.value}>
              <span className="flex items-center gap-2">
                <EntityKindIcon kind={type.value} className="w-4 h-4 shrink-0" style={{ color: type.color }} />
                <span>{type.label}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Value</Label>
      <Input
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

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Notes</Label>
      <textarea
        value={newEntity.notes}
        onChange={(e) => setNewEntity({ ...newEntity, notes: e.target.value })}
        className="mt-2 w-full bg-black/50 border border-white/10 text-white rounded-sm px-3 py-2 min-h-[60px] text-sm"
        placeholder="Additional notes"
      />
    </div>

    <Button
      onClick={onSubmit}
      className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-sm"
    >
      <Plus className="w-4 h-4 mr-2" />
      Add Entity
    </Button>
  </div>
);

export default EntitiesWorkspace;
