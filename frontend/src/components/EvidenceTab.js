import React, { useState, useEffect } from 'react';
import { Plus, Trash2, FileBox, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import axios, { API } from '../config/api';

const EVIDENCE_TYPES = [
  { value: 'screenshot', label: 'Screenshot', icon: '📸' },
  { value: 'document', label: 'Document', icon: '📄' },
  { value: 'social_post', label: 'Social Media Post', icon: '💬' },
  { value: 'web_archive', label: 'Web Archive', icon: '💾' },
  { value: 'metadata', label: 'Metadata Extract', icon: '📊' },
];

const EvidenceTab = ({ investigationId, refreshTrigger, onRefresh }) => {
  const [evidence, setEvidence] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newEvidence, setNewEvidence] = useState({
    evidence_type: 'screenshot',
    source_url: '',
    content: '',
    notes: '',
    entity_id: null,
    verification_status: 'unverified'
  });

  useEffect(() => {
    fetchData();
  }, [investigationId, refreshTrigger]);

  const fetchData = async () => {
    try {
      const [evidenceRes, entitiesRes] = await Promise.all([
        axios.get(`${API}/investigations/${investigationId}/evidence`),
        axios.get(`${API}/investigations/${investigationId}/entities`)
      ]);
      setEvidence(evidenceRes.data);
      setEntities(entitiesRes.data);
    } catch (error) {
      console.error('Failed to fetch evidence:', error);
      toast.error('Failed to load evidence');
    } finally {
      setLoading(false);
    }
  };

  const addEvidence = async () => {
    if (!newEvidence.content.trim() && !newEvidence.source_url.trim()) {
      toast.error('Content or source URL is required');
      return;
    }

    try {
      await axios.post(`${API}/investigations/${investigationId}/evidence`, newEvidence);
      toast.success('Evidence added successfully');
      setShowAddDialog(false);
      setNewEvidence({
        evidence_type: 'screenshot',
        source_url: '',
        content: '',
        notes: '',
        entity_id: null,
        verification_status: 'unverified'
      });
      fetchData();
      onRefresh();
    } catch (error) {
      console.error('Failed to add evidence:', error);
      toast.error('Failed to add evidence');
    }
  };

  const deleteEvidence = async (evidenceId) => {
    if (!window.confirm('Delete this evidence?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/evidence/${evidenceId}`);
      toast.success('Evidence deleted successfully');
      fetchData();
      onRefresh();
    } catch (error) {
      console.error('Failed to delete evidence:', error);
      toast.error('Failed to delete evidence');
    }
  };

  const getEvidenceTypeInfo = (type) => {
    return EVIDENCE_TYPES.find(t => t.value === type) || EVIDENCE_TYPES[0];
  };

  const getVerificationBadge = (status) => {
    const badges = {
      verified: { className: 'bg-[#14f195]/20 text-[#14f195] border-[#14f195]/30', label: 'Verified' },
      unverified: { className: 'bg-[#94a3b8]/20 text-[#94a3b8] border-[#94a3b8]/30', label: 'Unverified' },
      disputed: { className: 'bg-[#ff3b30]/20 text-[#ff3b30] border-[#ff3b30]/30', label: 'Disputed' }
    };
    return badges[status] || badges.unverified;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="h-full glass border border-[#00d9ff]/20 rounded-lg p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileBox className="w-6 h-6 text-[#00d9ff]" />
          <h2 className="text-2xl font-bold text-[#00d9ff]">Evidence Vault ({evidence.length})</h2>
        </div>

        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button
              data-testid="add-evidence-btn"
              className="bg-[#00d9ff] text-black hover:bg-[#00b8d9] shadow-[0_0_15px_rgba(0,217,255,0.3)] font-bold uppercase text-xs"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Evidence
            </Button>
          </DialogTrigger>
          <DialogContent className="glass-xl border-[#00d9ff]/20 text-white">
            <DialogHeader>
              <DialogTitle className="text-2xl text-[#00d9ff]">Add Evidence</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Evidence Type</Label>
                <Select value={newEvidence.evidence_type} onValueChange={(value) => setNewEvidence({ ...newEvidence, evidence_type: value })}>              <SelectTrigger className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                    {EVIDENCE_TYPES.map(type => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.icon} {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Link to Entity (Optional)</Label>
                <Select value={newEvidence.entity_id || ''} onValueChange={(value) => setNewEvidence({ ...newEvidence, entity_id: value || null })}>              <SelectTrigger className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white">
                    <SelectValue placeholder="No entity link" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0d1b2a] border-[#00d9ff]/20 text-white">
                    <SelectItem value="none">No entity link</SelectItem>
                    {entities.map(entity => (
                      <SelectItem key={entity.id} value={entity.id}>
                        {entity.label || entity.value}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Source URL</Label>
                <Input
                  value={newEvidence.source_url}
                  onChange={(e) => setNewEvidence({ ...newEvidence, source_url: e.target.value })}
                  className="mt-2 bg-[#0a1628] border-[#00d9ff]/20 text-white"
                  placeholder="https://..."
                />
              </div>

              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Content</Label>
                <textarea
                  value={newEvidence.content}
                  onChange={(e) => setNewEvidence({ ...newEvidence, content: e.target.value })}
                  className="mt-2 w-full bg-[#0a1628] border border-[#00d9ff]/20 text-white rounded-md px-4 py-2 min-h-[100px]"
                  placeholder="Evidence content or description"
                />
              </div>

              <div>
                <Label className="text-sm text-[#94a3b8] uppercase tracking-wider">Notes</Label>
                <textarea
                  value={newEvidence.notes}
                  onChange={(e) => setNewEvidence({ ...newEvidence, notes: e.target.value })}
                  className="mt-2 w-full bg-[#0a1628] border border-[#00d9ff]/20 text-white rounded-md px-4 py-2 min-h-[80px]"
                  placeholder="Additional notes"
                />
              </div>

              <Button
                onClick={addEvidence}
                className="w-full bg-[#00d9ff] text-black hover:bg-[#00b8d9] font-bold uppercase"
              >
                Add Evidence
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
        </div>
      ) : evidence.length === 0 ? (
        <div className="text-center py-20">
          <FileBox className="w-16 h-16 text-[#94a3b8] mx-auto mb-4 opacity-50" />
          <p className="text-[#94a3b8]">No evidence added yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {evidence.map(item => {
            const typeInfo = getEvidenceTypeInfo(item.evidence_type);
            const verificationBadge = getVerificationBadge(item.verification_status);
            const linkedEntity = item.entity_id ? entities.find(e => e.id === item.entity_id) : null;

            return (
              <div
                key={item.id}
                data-testid={`evidence-item-${item.id}`}
                className="bg-[#0d1b2a]/50 border border-[#00d9ff]/20 rounded-lg p-4 hover:border-[#00d9ff]/40 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">{typeInfo.icon}</div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className="bg-[#00d9ff]/20 text-[#00d9ff] border border-[#00d9ff]/30 text-xs">
                          {typeInfo.label}
                        </Badge>
                        <Badge className={`border text-xs ${verificationBadge.className}`}>
                          {verificationBadge.label}
                        </Badge>
                      </div>
                      {linkedEntity && (
                        <p className="text-xs text-[#94a3b8] mt-1">
                          Linked to: <span className="text-[#00d9ff]">{linkedEntity.label || linkedEntity.value}</span>
                        </p>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteEvidence(item.id)}
                    className="text-[#ff3b30] hover:text-white hover:bg-[#ff3b30]/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                {item.content && (
                  <p className="text-sm text-white mb-3 bg-[#0a1628]/50 p-3 rounded border border-[#00d9ff]/10">
                    {item.content}
                  </p>
                )}

                {item.source_url && (
                  <div className="flex items-center gap-2 mb-2">
                    <ExternalLink className="w-4 h-4 text-[#94a3b8]" />
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-[#00d9ff] hover:underline font-mono"
                    >
                      {item.source_url}
                    </a>
                  </div>
                )}

                {item.notes && (
                  <p className="text-sm text-[#94a3b8] mt-2 italic">{item.notes}</p>
                )}

                <p className="text-xs text-[#94a3b8] mt-3 pt-3 border-t border-[#00d9ff]/10">
                  Collected: {formatDate(item.collected_at)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EvidenceTab;
