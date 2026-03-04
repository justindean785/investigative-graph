import React, { useState } from 'react';
import { Search, Plus, Trash2, ChevronRight, Users, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';

const ENTITY_TYPES = [
  { value: 'person', label: 'Person', icon: '👤', color: '#06b6d4' },
  { value: 'email', label: 'Email', icon: '📧', color: '#14f195' },
  { value: 'phone', label: 'Phone', icon: '📱', color: '#f97316' },
  { value: 'domain', label: 'Domain', icon: '🌐', color: '#06b6d4' },
  { value: 'ip', label: 'IP Address', icon: '🖥️', color: '#7c3aed' },
  { value: 'username', label: 'Username', icon: '👨‍💻', color: '#14f195' },
  { value: 'company', label: 'Company', icon: '🏢', color: '#f97316' },
  { value: 'wallet', label: 'Wallet', icon: '💰', color: '#fbbf24' },
  { value: 'social', label: 'Social Account', icon: '💬', color: '#3b82f6' },
  { value: 'url', label: 'URL', icon: '🔗', color: '#06b6d4' },
];

const EntitiesPanel = ({ investigationId }) => {
  const {
    entities,
    relationships,
    addEntity,
    removeEntity,
    selectEntity,
    ui,
  } = useInvestigationStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [expandedEntity, setExpandedEntity] = useState(null);
  const [newEntity, setNewEntity] = useState({
    entity_type: 'person',
    value: '',
    label: '',
    notes: '',
    confidence: 0.5,
    risk_score: 0
  });

  const filteredEntities = entities.filter(entity =>
    entity.value.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (entity.label && entity.label.toLowerCase().includes(searchQuery.toLowerCase())) ||
    entity.kind.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getEntityTypeInfo = (type) => {
    return ENTITY_TYPES.find(t => t.value === type) || ENTITY_TYPES[0];
  };

  const getEntityConnections = (entityId) => {
    return relationships.filter(r => r.fromId === entityId || r.toId === entityId);
  };

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
        risk: newEntity.risk_score * 100,
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
        risk_score: 0
      });
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  const handleDeleteEntity = async (entityId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this entity?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/entities/${entityId}`);
      removeEntity(entityId);
      toast.success('Entity deleted');
    } catch (error) {
      toast.error('Failed to delete entity');
    }
  };

  // Group entities by type
  const groupedEntities = filteredEntities.reduce((acc, entity) => {
    const type = entity.kind;
    if (!acc[type]) acc[type] = [];
    acc[type].push(entity);
    return acc;
  }, {});

  return (
    <aside className="w-72 border-l border-white/5 bg-black/50 flex flex-col z-10 flex-shrink-0" data-testid="entities-panel">
      {/* Header */}
      <div className="p-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Entities</span>
          </div>
          <Badge variant="secondary" className="bg-primary/10 text-primary border-0 text-xs">
            {entities.length}
          </Badge>
        </div>
        
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 bg-[#0a0a0a] border-white/10 h-8 text-xs"
            placeholder="Filter entities..."
          />
        </div>
      </div>

      {/* Add Entity Button */}
      <div className="p-2 border-b border-white/5">
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button 
              data-testid="panel-add-entity-btn"
              className="w-full bg-primary/10 text-primary hover:bg-primary/20 text-xs h-8 rounded-sm"
            >
              <Plus className="w-3 h-3 mr-1.5" />
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
                  <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
                    {ENTITY_TYPES.map(type => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.icon} {type.label}
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
                onClick={handleAddEntity}
                className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow"
              >
                Add Entity
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Entity List */}
      <div className="flex-1 overflow-y-auto p-2">
        {filteredEntities.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-slate-500">No entities found</p>
          </div>
        ) : (
          <div className="space-y-1">
            {Object.entries(groupedEntities).map(([type, typeEntities]) => {
              const typeInfo = getEntityTypeInfo(type);
              return (
                <div key={type} className="mb-3">
                  <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-slate-500 uppercase tracking-wider">
                    <span>{typeInfo.icon}</span>
                    <span>{typeInfo.label}</span>
                    <span className="text-slate-600">({typeEntities.length})</span>
                  </div>
                  
                  {typeEntities.map(entity => {
                    const connections = getEntityConnections(entity.id);
                    const isExpanded = expandedEntity === entity.id;
                    const isSelected = ui.selectedEntityId === entity.id;
                    
                    return (
                      <div key={entity.id}>
                        <div
                          data-testid={`entity-item-${entity.id}`}
                          onClick={() => {
                            selectEntity(entity.id);
                            setExpandedEntity(isExpanded ? null : entity.id);
                          }}
                          className={`flex items-center gap-2 px-2 py-1.5 rounded-sm cursor-pointer transition-colors group ${
                            isSelected 
                              ? 'bg-primary/10 border-l-2 border-primary' 
                              : 'hover:bg-white/5'
                          }`}
                        >
                          <ChevronRight className={`w-3 h-3 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white truncate">
                              {entity.label || entity.value}
                            </p>
                            {entity.label && entity.label !== entity.value && (
                              <p className="text-xs text-slate-500 font-mono truncate">
                                {entity.value}
                              </p>
                            )}
                          </div>
                          {connections.length > 0 && (
                            <Badge variant="secondary" className="bg-white/5 text-slate-400 border-0 text-[10px] px-1.5">
                              {connections.length}
                            </Badge>
                          )}
                          {entity.risk > 50 && (
                            <div className="w-2 h-2 rounded-full bg-red-500"></div>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleDeleteEntity(entity.id, e)}
                            className="h-5 w-5 p-0 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                        
                        {/* Expanded Details */}
                        {isExpanded && (
                          <div className="ml-5 pl-3 border-l border-white/5 py-2 space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-500">Confidence</span>
                              <div className="flex items-center gap-1.5">
                                <div className="w-16 h-1 bg-black/50 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-primary" 
                                    style={{ width: `${entity.confidence * 100}%` }}
                                  />
                                </div>
                                <span className="text-slate-400 font-mono">{Math.round(entity.confidence * 100)}%</span>
                              </div>
                            </div>
                            
                            {entity.risk > 0 && (
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Risk</span>
                                <div className="flex items-center gap-1.5">
                                  <div className="w-16 h-1 bg-black/50 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-red-500" 
                                      style={{ width: `${entity.risk}%` }}
                                    />
                                  </div>
                                  <span className="text-red-400 font-mono">{Math.round(entity.risk)}%</span>
                                </div>
                              </div>
                            )}
                            
                            {connections.length > 0 && (
                              <div className="pt-1">
                                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Connections</span>
                                <div className="mt-1 space-y-0.5">
                                  {connections.slice(0, 3).map(conn => {
                                    const targetId = conn.fromId === entity.id ? conn.toId : conn.fromId;
                                    const targetEntity = entities.find(e => e.id === targetId);
                                    return (
                                      <div key={conn.id} className="flex items-center gap-1 text-xs text-slate-400">
                                        <ExternalLink className="w-2.5 h-2.5" />
                                        <span className="truncate">{targetEntity?.label || targetEntity?.value || 'Unknown'}</span>
                                      </div>
                                    );
                                  })}
                                  {connections.length > 3 && (
                                    <p className="text-[10px] text-slate-500">+{connections.length - 3} more</p>
                                  )}
                                </div>
                              </div>
                            )}
                            
                            {entity.notes && (
                              <p className="text-xs text-slate-400 italic">{entity.notes}</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};

export default EntitiesPanel;
