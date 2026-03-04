import React, { useState } from 'react';
import { FileBox, Plus, Link2, Image, Globe, FileText, Wallet, Archive, MessageSquare, Trash2, ExternalLink, ChevronRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';

const EVIDENCE_TYPES = [
  { value: 'screenshot', label: 'Screenshot', icon: Image, color: '#06b6d4' },
  { value: 'webpage', label: 'Web Page', icon: Globe, color: '#14f195' },
  { value: 'document', label: 'Document', icon: FileText, color: '#f97316' },
  { value: 'social_post', label: 'Social Media Post', icon: MessageSquare, color: '#3b82f6' },
  { value: 'blockchain_tx', label: 'Blockchain Transaction', icon: Wallet, color: '#fbbf24' },
  { value: 'web_archive', label: 'Archive Link', icon: Archive, color: '#7c3aed' },
  { value: 'link', label: 'Link / URL', icon: Link2, color: '#06b6d4' },
];

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

const EvidenceWorkspace = ({ investigationId, onNavigateToEntities }) => {
  const { evidence, entities, addEvidence, addEntity, removeEvidence } = useInvestigationStore();
  
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showExtractDialog, setShowExtractDialog] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [expandedEvidence, setExpandedEvidence] = useState(null);
  
  const [newEvidence, setNewEvidence] = useState({
    evidence_type: 'screenshot',
    title: '',
    source_url: '',
    content: '',
    notes: '',
  });

  const [extractEntity, setExtractEntity] = useState({
    entity_type: 'email',
    value: '',
    label: '',
  });

  const getTypeInfo = (type) => EVIDENCE_TYPES.find(t => t.value === type) || EVIDENCE_TYPES[0];

  const handleAddEvidence = async () => {
    if (!newEvidence.title.trim() && !newEvidence.source_url.trim() && !newEvidence.content.trim()) {
      toast.error('Please provide a title, URL, or content');
      return;
    }

    try {
      const payload = {
        evidence_type: newEvidence.evidence_type,
        source_url: newEvidence.source_url,
        content: newEvidence.content || newEvidence.title,
        notes: newEvidence.notes,
      };

      const response = await axios.post(`${API}/investigations/${investigationId}/evidence`, payload);
      
      addEvidence({
        id: response.data.id,
        type: newEvidence.evidence_type,
        title: newEvidence.title || newEvidence.evidence_type,
        sourceUrl: newEvidence.source_url,
        content: newEvidence.content,
        notes: newEvidence.notes,
        hash: '',
        linked: { entityIds: [], edgeIds: [] },
        collectedAt: new Date().toISOString(),
      });

      toast.success('Evidence added to investigation');
      setShowAddDialog(false);
      setNewEvidence({
        evidence_type: 'screenshot',
        title: '',
        source_url: '',
        content: '',
        notes: '',
      });
    } catch (error) {
      console.error('Failed to add evidence:', error);
      toast.error('Failed to add evidence');
    }
  };

  const handleExtractEntity = async () => {
    if (!extractEntity.value.trim()) {
      toast.error('Entity value is required');
      return;
    }

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/entities`, {
        entity_type: extractEntity.entity_type,
        value: extractEntity.value,
        label: extractEntity.label || extractEntity.value,
        notes: `Extracted from evidence: ${selectedEvidence?.title || 'Unknown'}`,
        confidence: 0.7,
      });
      
      addEntity({
        id: response.data.id,
        kind: extractEntity.entity_type,
        value: extractEntity.value,
        label: extractEntity.label || extractEntity.value,
        notes: `Extracted from evidence`,
        tags: [],
        sources: [selectedEvidence?.id],
        confidence: 0.7,
        risk: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      toast.success('Entity extracted and added');
      setShowExtractDialog(false);
      setExtractEntity({ entity_type: 'email', value: '', label: '' });
    } catch (error) {
      console.error('Failed to extract entity:', error);
      toast.error('Failed to extract entity');
    }
  };

  const handleDeleteEvidence = async (evidenceId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this evidence?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/evidence/${evidenceId}`);
      removeEvidence(evidenceId);
      toast.success('Evidence deleted');
    } catch (error) {
      toast.error('Failed to delete evidence');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Empty state
  if (evidence.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-6">
            <FileBox className="w-10 h-10 text-primary" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            Start Building Your Investigation
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            Add evidence such as links, screenshots, documents, or OSINT findings.
            Entities and relationships will be extracted and visualized automatically.
          </p>

          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-first-evidence-btn"
                className="bg-primary hover:bg-primary/90 text-white px-8 h-12 rounded-sm shadow-glow text-base"
              >
                <Plus className="w-5 h-5 mr-2" />
                Add Evidence
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-lg">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Add Evidence</DialogTitle>
              </DialogHeader>
              <EvidenceForm 
                newEvidence={newEvidence} 
                setNewEvidence={setNewEvidence} 
                onSubmit={handleAddEvidence}
              />
            </DialogContent>
          </Dialog>

          <div className="mt-10 grid grid-cols-3 gap-4">
            {EVIDENCE_TYPES.slice(0, 6).map(type => (
              <div 
                key={type.value}
                className="p-3 rounded-sm bg-white/5 border border-white/5 text-center"
              >
                <type.icon className="w-5 h-5 mx-auto mb-2" style={{ color: type.color }} />
                <span className="text-xs text-slate-400">{type.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <FileBox className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-heading font-bold text-white">Evidence Collection</h2>
          <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
            {evidence.length} items
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {entities.length > 0 && (
            <Button
              variant="outline"
              onClick={onNavigateToEntities}
              className="border-white/10 text-slate-300 hover:bg-white/5 text-xs h-8"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
              View {entities.length} Entities
            </Button>
          )}
          
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-evidence-btn"
                className="bg-primary hover:bg-primary/90 text-white text-xs h-8 rounded-sm shadow-glow"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Add Evidence
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-lg">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Add Evidence</DialogTitle>
              </DialogHeader>
              <EvidenceForm 
                newEvidence={newEvidence} 
                setNewEvidence={setNewEvidence} 
                onSubmit={handleAddEvidence}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Evidence List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {evidence.map(item => {
            const typeInfo = getTypeInfo(item.type);
            const isExpanded = expandedEvidence === item.id;
            const linkedEntities = entities.filter(e => item.linked?.entityIds?.includes(e.id));

            return (
              <div 
                key={item.id}
                data-testid={`evidence-item-${item.id}`}
                className="bg-black/40 border border-white/10 rounded-sm overflow-hidden hover:border-white/20 transition-colors"
              >
                <div 
                  className="p-4 cursor-pointer"
                  onClick={() => setExpandedEvidence(isExpanded ? null : item.id)}
                >
                  <div className="flex items-start gap-4">
                    <div 
                      className="w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: `${typeInfo.color}15`, border: `1px solid ${typeInfo.color}30` }}
                    >
                      <typeInfo.icon className="w-5 h-5" style={{ color: typeInfo.color }} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-white font-medium truncate">
                          {item.title || item.content?.slice(0, 50) || typeInfo.label}
                        </h3>
                        <Badge className="bg-white/5 text-slate-400 border-0 text-[10px]">
                          {typeInfo.label}
                        </Badge>
                      </div>

                      {item.sourceUrl && (
                        <a 
                          href={item.sourceUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-primary hover:underline font-mono flex items-center gap-1 mb-2"
                          onClick={e => e.stopPropagation()}
                        >
                          <ExternalLink className="w-3 h-3" />
                          {item.sourceUrl.slice(0, 50)}...
                        </a>
                      )}

                      {item.content && (
                        <p className="text-sm text-slate-400 line-clamp-2">{item.content}</p>
                      )}

                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-xs text-slate-500">
                          {formatDate(item.collectedAt)}
                        </span>
                        {linkedEntities.length > 0 && (
                          <span className="text-xs text-primary">
                            {linkedEntities.length} linked entities
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <ChevronRight className={`w-4 h-4 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteEvidence(item.id, e)}
                        className="h-7 w-7 p-0 text-slate-500 hover:text-red-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Expanded Actions */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-white/5 bg-white/[0.02]">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-slate-500 uppercase tracking-wider">
                        Extract entities from this evidence
                      </div>
                      <Button
                        onClick={() => {
                          setSelectedEvidence(item);
                          setShowExtractDialog(true);
                        }}
                        className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 text-xs h-8"
                      >
                        <Plus className="w-3.5 h-3.5 mr-1.5" />
                        Extract Entity
                      </Button>
                    </div>

                    {linkedEntities.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {linkedEntities.map(entity => (
                          <Badge 
                            key={entity.id}
                            className="bg-primary/10 text-primary border border-primary/20"
                          >
                            {ENTITY_TYPES.find(t => t.value === entity.kind)?.icon} {entity.label}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Extract Entity Dialog */}
      <Dialog open={showExtractDialog} onOpenChange={setShowExtractDialog}>
        <DialogContent className="glass-strong border-white/10 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-heading">Extract Entity</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="p-3 bg-white/5 rounded-sm border border-white/10">
              <span className="text-xs text-slate-500 uppercase tracking-wider">From Evidence</span>
              <p className="text-sm text-white mt-1">{selectedEvidence?.title || selectedEvidence?.content?.slice(0, 50)}</p>
            </div>

            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Entity Type</Label>
              <Select value={extractEntity.entity_type} onValueChange={(value) => setExtractEntity({ ...extractEntity, entity_type: value })}>
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
                value={extractEntity.value}
                onChange={(e) => setExtractEntity({ ...extractEntity, value: e.target.value })}
                className="mt-2 bg-black/50 border-white/10 text-white"
                placeholder="e.g., john@example.com"
              />
            </div>

            <div>
              <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Label (Optional)</Label>
              <Input
                value={extractEntity.label}
                onChange={(e) => setExtractEntity({ ...extractEntity, label: e.target.value })}
                className="mt-2 bg-black/50 border-white/10 text-white"
                placeholder="Display name"
              />
            </div>

            <Button
              onClick={handleExtractEntity}
              className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              Extract Entity
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Evidence Form Component
const EvidenceForm = ({ newEvidence, setNewEvidence, onSubmit }) => (
  <div className="space-y-4 mt-4">
    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Evidence Type</Label>
      <Select value={newEvidence.evidence_type} onValueChange={(value) => setNewEvidence({ ...newEvidence, evidence_type: value })}>
        <SelectTrigger className="mt-2 bg-black/50 border-white/10 text-white">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
          {EVIDENCE_TYPES.map(type => (
            <SelectItem key={type.value} value={type.value}>
              <div className="flex items-center gap-2">
                <type.icon className="w-4 h-4" style={{ color: type.color }} />
                {type.label}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Title</Label>
      <Input
        value={newEvidence.title}
        onChange={(e) => setNewEvidence({ ...newEvidence, title: e.target.value })}
        className="mt-2 bg-black/50 border-white/10 text-white"
        placeholder="Evidence title"
      />
    </div>

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Source URL</Label>
      <Input
        value={newEvidence.source_url}
        onChange={(e) => setNewEvidence({ ...newEvidence, source_url: e.target.value })}
        className="mt-2 bg-black/50 border-white/10 text-white"
        placeholder="https://..."
      />
    </div>

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Description / Content</Label>
      <textarea
        value={newEvidence.content}
        onChange={(e) => setNewEvidence({ ...newEvidence, content: e.target.value })}
        className="mt-2 w-full bg-black/50 border border-white/10 text-white rounded-sm px-3 py-2 min-h-[100px] text-sm"
        placeholder="Describe the evidence or paste content..."
      />
    </div>

    <div>
      <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Notes (Optional)</Label>
      <Input
        value={newEvidence.notes}
        onChange={(e) => setNewEvidence({ ...newEvidence, notes: e.target.value })}
        className="mt-2 bg-black/50 border-white/10 text-white"
        placeholder="Additional notes"
      />
    </div>

    <Button
      onClick={onSubmit}
      className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow h-10"
    >
      <Plus className="w-4 h-4 mr-2" />
      Add Evidence
    </Button>
  </div>
);

export default EvidenceWorkspace;
