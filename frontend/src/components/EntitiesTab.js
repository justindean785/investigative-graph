import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import axios, { API } from '../config/api';

const ENTITY_TYPES = [
  { value: 'person', label: 'Person', icon: '👤' },
  { value: 'email', label: 'Email', icon: '📧' },
  { value: 'phone', label: 'Phone', icon: '📱' },
  { value: 'domain', label: 'Domain', icon: '🌐' },
  { value: 'ip', label: 'IP Address', icon: '🖥️' },
  { value: 'username', label: 'Username', icon: '👨‍💻' },
  { value: 'company', label: 'Company', icon: '🏢' },
  { value: 'wallet', label: 'Wallet', icon: '💰' },
  { value: 'social', label: 'Social Account', icon: '💬' },
  { value: 'url', label: 'URL', icon: '🔗' },
];

const EntitiesTab = ({ investigationId, refreshTrigger, onRefresh }) => {
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newEntity, setNewEntity] = useState({
    entity_type: 'person',
    value: '',
    label: '',
    notes: '',
    confidence: 0.5,
    risk_score: 0
  });

  useEffect(() => {
    fetchEntities();
  }, [investigationId, refreshTrigger]);

  const fetchEntities = async () => {
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/entities`);
      setEntities(response.data);
    } catch (error) {
      console.error('Failed to fetch entities:', error);
      toast.error('Failed to load entities');
    } finally {
      setLoading(false);
    }
  };

  const addEntity = async () => {
    if (!newEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }

    try {
      await axios.post(`${API}/investigations/${investigationId}/entities`, newEntity);
      toast.success('Entity added successfully');
      setShowAddDialog(false);
      setNewEntity({
        entity_type: 'person',
        value: '',
        label: '',
        notes: '',
        confidence: 0.5,
        risk_score: 0
      });
      fetchEntities();
      onRefresh();
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  const deleteEntity = async (entityId) => {
    if (!window.confirm('Delete this entity and its relationships?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/entities/${entityId}`);
      toast.success('Entity deleted successfully');
      fetchEntities();
      onRefresh();
    } catch (error) {
      console.error('Failed to delete entity:', error);
      toast.error('Failed to delete entity');
    }
  };

  const filteredEntities = entities.filter(entity =>
    entity.value.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (entity.label && entity.label.toLowerCase().includes(searchQuery.toLowerCase())) ||
    entity.entity_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getEntityTypeInfo = (type) => {
    return ENTITY_TYPES.find(t => t.value === type) || ENTITY_TYPES[0];
  };

  return (
    <div className="h-full glass border border-[#00d9ff]/20 rounded-lg p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-[#00d9ff]">Entities ({entities.length})</h2>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button
              data-testid="add-entity-dialog-btn"
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
                <Select value={newEntity.entity_type} onValueChange={(value) => setNewEntity({ ...newEntity, entity_type: value })}>              <SelectTrigger className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
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

              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Notes</Label>
                <textarea
                  value={newEntity.notes}
                  onChange={(e) => setNewEntity({ ...newEntity, notes: e.target.value })}
                  className="mt-2 w-full bg-[#0a1628] border border-[#00d9ff]/20 text-white rounded-md px-4 py-2 min-h-[80px]"
                  placeholder="Additional notes"
                />
              </div>

              <Button
                onClick={addEntity}
                className="w-full bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase"
              >
                Add Entity
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#94a3b8]" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-12 bg-[#0d1b2a]/50 border-transparent focus:border-[#00d9ff]/40 rounded-full text-white"
            placeholder="Search entities..."
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
        </div>
      ) : filteredEntities.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-[#94a3b8]">No entities found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEntities.map(entity => {
            const typeInfo = getEntityTypeInfo(entity.entity_type);
            return (
              <div
                key={entity.id}
                data-testid={`entity-item-${entity.id}`}
                className="bg-[#0d1b2a]/50 border border-[#00d9ff]/20 rounded-lg p-4 hover:border-[#00d9ff]/40 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-3xl">{typeInfo.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-white font-bold">{entity.label || entity.value}</h3>
                        <Badge className="bg-[#00d9ff]/20 text-[#00d9ff] border border-[#00d9ff]/30 text-xs">
                          {typeInfo.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-[#94a3b8] font-mono mb-2">{entity.value}</p>
                      {entity.notes && (
                        <p className="text-sm text-[#94a3b8] mt-2">{entity.notes}</p>
                      )}
                      <div className="flex items-center gap-4 mt-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[#94a3b8]">Confidence:</span>
                          <div className="w-24 h-2 bg-[#0a1628] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#00d9ff]"
                              style={{ width: `${entity.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-white">{Math.round(entity.confidence * 100)}%</span>
                        </div>
                        {entity.risk_score > 0 && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-[#94a3b8]">Risk:</span>
                            <div className="w-24 h-2 bg-[#0a1628] rounded-full overflow-hidden">
                              <div
                                className="h-full bg-[#ff3b30]"
                                style={{ width: `${entity.risk_score * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-[#ff3b30]">{Math.round(entity.risk_score * 100)}%</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteEntity(entity.id)}
                    className="text-[#ff3b30] hover:text-white hover:bg-[#ff3b30]/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EntitiesTab;
