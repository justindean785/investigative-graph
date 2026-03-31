import React, { useState, useCallback } from 'react';
import { 
  FileBox, Plus, Link2, Image, Globe, FileText, Wallet, Archive, MessageSquare, 
  Trash2, ExternalLink, ChevronRight, Sparkles, Upload, ClipboardPaste, Loader2,
  CheckCircle, User, Phone, Mail, Server, Hash, Eye, AlertTriangle, X
} from 'lucide-react';
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

// Expanded evidence categories
const EVIDENCE_CATEGORIES = {
  web: {
    label: "Web Evidence",
    icon: Globe,
    color: "#06b6d4",
    types: [
      { value: "webpage", label: "Web Page" },
      { value: "screenshot", label: "Website Screenshot" },
      { value: "url", label: "URL" },
      { value: "forum_post", label: "Forum Post" },
      { value: "blog_article", label: "Blog Article" },
      { value: "paste_site", label: "Paste Site Content" },
    ]
  },
  social: {
    label: "Social Media",
    icon: MessageSquare,
    color: "#3b82f6",
    types: [
      { value: "social_profile", label: "Social Profile" },
      { value: "social_post", label: "Social Post" },
      { value: "social_comment", label: "Comment" },
      { value: "thread", label: "Thread" },
      { value: "video_post", label: "Video Post" },
    ]
  },
  identity: {
    label: "Identity",
    icon: User,
    color: "#14f195",
    types: [
      { value: "email_evidence", label: "Email Address" },
      { value: "username_evidence", label: "Username" },
      { value: "phone_evidence", label: "Phone Number" },
      { value: "alias", label: "Alias" },
      { value: "real_name", label: "Real Name" },
    ]
  },
  crypto: {
    label: "Crypto / Financial",
    icon: Wallet,
    color: "#fbbf24",
    types: [
      { value: "crypto_wallet", label: "Crypto Wallet" },
      { value: "blockchain_tx", label: "Blockchain TX" },
      { value: "exchange_account", label: "Exchange Account" },
      { value: "payment_screenshot", label: "Payment Screenshot" },
    ]
  },
  infrastructure: {
    label: "Infrastructure",
    icon: Server,
    color: "#f97316",
    types: [
      { value: "domain_evidence", label: "Domain" },
      { value: "ip_evidence", label: "IP Address" },
      { value: "server", label: "Server" },
      { value: "dns_record", label: "DNS Record" },
      { value: "whois_record", label: "WHOIS Record" },
    ]
  },
  files: {
    label: "Files & Media",
    icon: FileText,
    color: "#7c3aed",
    types: [
      { value: "document", label: "Document" },
      { value: "pdf", label: "PDF" },
      { value: "photo", label: "Photo" },
      { value: "video", label: "Video" },
      { value: "audio", label: "Audio" },
    ]
  },
  communication: {
    label: "Communication",
    icon: Mail,
    color: "#ec4899",
    types: [
      { value: "email_message", label: "Email Message" },
      { value: "chat_log", label: "Chat Log" },
      { value: "sms_message", label: "SMS Message" },
      { value: "telegram_chat", label: "Telegram Chat" },
      { value: "discord_message", label: "Discord Message" },
    ]
  },
  notes: {
    label: "Analyst Notes",
    icon: FileBox,
    color: "#94a3b8",
    types: [
      { value: "analyst_note", label: "Analyst Note" },
      { value: "observation", label: "Observation" },
      { value: "hypothesis", label: "Hypothesis" },
      { value: "lead_note", label: "Lead" },
    ]
  }
};

const ENTITY_TYPE_ICONS = {
  email: { icon: Mail, color: '#06b6d4' },
  domain: { icon: Globe, color: '#14f195' },
  ip: { icon: Server, color: '#f97316' },
  wallet: { icon: Wallet, color: '#fbbf24' },
  phone: { icon: Phone, color: '#3b82f6' },
  username: { icon: User, color: '#7c3aed' },
  url: { icon: Link2, color: '#06b6d4' },
  social: { icon: MessageSquare, color: '#ec4899' },
  hash: { icon: Hash, color: '#94a3b8' },
};

const EvidenceWorkspace = ({ investigationId, onNavigateToEntities }) => {
  const { evidence, entities, addEvidence, addEntity, removeEvidence, updateEvidence } = useInvestigationStore();
  const { confirm, dialogProps, ConfirmDialog } = useConfirmDialog();
  
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showQuickIngest, setShowQuickIngest] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState(null);
  const [detectedEntities, setDetectedEntities] = useState([]);
  const [showDetectedPanel, setShowDetectedPanel] = useState(false);
  const [processingEvidence, setProcessingEvidence] = useState(null);
  
  // Quick ingest states
  const [quickMode, setQuickMode] = useState('url'); // url, text, file
  const [quickUrl, setQuickUrl] = useState('');
  const [quickText, setQuickText] = useState('');
  const [quickTitle, setQuickTitle] = useState('');
  const [quickLoading, setQuickLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  
  const [selectedCategory, setSelectedCategory] = useState('web');
  const [newEvidence, setNewEvidence] = useState({
    evidence_type: 'webpage',
    title: '',
    source_url: '',
    content: '',
    notes: '',
  });

  // Get all evidence types as flat list
  const getAllTypes = () => {
    return Object.values(EVIDENCE_CATEGORIES).flatMap(cat => 
      cat.types.map(t => ({ ...t, categoryColor: cat.color }))
    );
  };

  const getTypeInfo = (type) => {
    for (const cat of Object.values(EVIDENCE_CATEGORIES)) {
      const found = cat.types.find(t => t.value === type);
      if (found) return { ...found, color: cat.color, icon: cat.icon };
    }
    return { value: type, label: type, color: '#94a3b8', icon: FileBox };
  };

  // Quick URL Ingest
  const handleQuickUrlIngest = async () => {
    if (!quickUrl.trim()) {
      toast.error('Please enter a URL');
      return;
    }

    setQuickLoading(true);
    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/ingest/url`, {
        url: quickUrl,
        evidence_type: 'webpage'
      });

      if (response.data.success) {
        // Add evidence to store
        addEvidence({
          id: response.data.evidence.id,
          type: response.data.evidence.type,
          title: response.data.evidence.title,
          sourceUrl: quickUrl,
          content: '',
          notes: '',
          hash: '',
          linked: { entityIds: [], edgeIds: [] },
          collectedAt: new Date().toISOString(),
        });

        // Handle detected entities
        if (response.data.detected_entities?.length > 0) {
          setDetectedEntities(response.data.detected_entities);
          setProcessingEvidence(response.data.evidence.id);
          setShowDetectedPanel(true);
          toast.success(`URL ingested! ${response.data.detected_entities.length} indicators detected`);
        } else {
          toast.success('URL ingested successfully');
        }

        setQuickUrl('');
        setShowQuickIngest(false);
      }
    } catch (error) {
      console.error('URL ingest failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to ingest URL');
    } finally {
      setQuickLoading(false);
    }
  };

  // Quick Text Ingest
  const handleQuickTextIngest = async () => {
    if (!quickText.trim()) {
      toast.error('Please enter some text');
      return;
    }

    setQuickLoading(true);
    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/ingest/text`, {
        content: quickText,
        title: quickTitle || 'Raw Text',
        evidence_type: 'analyst_note'
      });

      if (response.data.success) {
        addEvidence({
          id: response.data.evidence.id,
          type: response.data.evidence.type,
          title: response.data.evidence.title,
          sourceUrl: '',
          content: quickText,
          notes: '',
          hash: '',
          linked: { entityIds: [], edgeIds: [] },
          collectedAt: new Date().toISOString(),
        });

        if (response.data.detected_entities?.length > 0) {
          setDetectedEntities(response.data.detected_entities);
          setProcessingEvidence(response.data.evidence.id);
          setShowDetectedPanel(true);
          toast.success(`Text ingested! ${response.data.detected_entities.length} indicators detected`);
        } else {
          toast.success('Text ingested successfully');
        }

        setQuickText('');
        setQuickTitle('');
        setShowQuickIngest(false);
      }
    } catch (error) {
      console.error('Text ingest failed:', error);
      toast.error('Failed to ingest text');
    } finally {
      setQuickLoading(false);
    }
  };

  // File Upload Handler
  const handleFileUpload = async (file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('evidence_type', 'document');
    formData.append('notes', '');

    setQuickLoading(true);
    try {
      const response = await axios.post(
        `${API}/investigations/${investigationId}/ingest/file`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      if (response.data.success) {
        addEvidence({
          id: response.data.evidence.id,
          type: response.data.evidence.type,
          title: response.data.evidence.filename,
          sourceUrl: '',
          content: response.data.evidence.text_extracted ? 'Text extracted' : 'Binary file',
          notes: '',
          hash: '',
          linked: { entityIds: [], edgeIds: [] },
          collectedAt: new Date().toISOString(),
        });

        if (response.data.detected_entities?.length > 0) {
          setDetectedEntities(response.data.detected_entities);
          setProcessingEvidence(response.data.evidence.id);
          setShowDetectedPanel(true);
          toast.success(`File uploaded! ${response.data.detected_entities.length} indicators detected`);
        } else {
          toast.success('File uploaded successfully');
        }

        setShowQuickIngest(false);
      }
    } catch (error) {
      console.error('File upload failed:', error);
      toast.error('Failed to upload file');
    } finally {
      setQuickLoading(false);
    }
  };

  // Drag and Drop handlers
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Add detected entity to investigation
  const handleAddDetectedEntity = async (entity) => {
    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/entities`, {
        entity_type: entity.type,
        value: entity.value,
        label: entity.label || entity.value,
        notes: `Extracted from evidence`,
        confidence: entity.confidence || 0.85,
        risk_score: entity.risk_score || 0.3,
        sources: processingEvidence ? [processingEvidence] : []
      });

      addEntity({
        id: response.data.id,
        kind: entity.type,
        value: entity.value,
        label: entity.label || entity.value,
        notes: `Extracted from evidence`,
        tags: [],
        sources: processingEvidence ? [processingEvidence] : [],
        confidence: entity.confidence || 0.85,
        risk: entity.risk_score || 0.3,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      // Remove from detected list
      setDetectedEntities(prev => prev.filter(e => e.value !== entity.value));
      toast.success(`Added ${entity.type}: ${entity.value}`);
    } catch (error) {
      console.error('Failed to add entity:', error);
      toast.error('Failed to add entity');
    }
  };

  // Add all detected entities
  const handleAddAllDetected = async () => {
    if (detectedEntities.length === 0) return;

    try {
      const entitiesToAdd = detectedEntities.map(e => ({
        entity_type: e.type,
        value: e.value,
        label: e.label || e.value,
        notes: 'Extracted from evidence',
        confidence: e.confidence || 0.85,
        risk_score: e.risk_score || 0.3,
        sources: processingEvidence ? [processingEvidence] : []
      }));

      const response = await axios.post(
        `${API}/investigations/${investigationId}/entities/batch`,
        entitiesToAdd
      );

      if (response.data.success) {
        response.data.entities.forEach(entity => {
          addEntity({
            id: entity.id,
            kind: entity.entity_type,
            value: entity.value,
            label: entity.label || entity.value,
            notes: entity.notes,
            tags: [],
            sources: entity.sources || [],
            confidence: entity.confidence,
            risk: entity.risk_score,
            createdAt: entity.created_at,
            updatedAt: entity.created_at,
          });
        });

        setDetectedEntities([]);
        setShowDetectedPanel(false);
        toast.success(`Added ${response.data.created_count} entities`);
      }
    } catch (error) {
      console.error('Failed to add entities:', error);
      toast.error('Failed to add entities');
    }
  };

  // Regular evidence add
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
        evidence_type: 'webpage',
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

  const handleDeleteEvidence = (evidenceId, e) => {
    e.stopPropagation();
    confirm({
      title: 'Delete Evidence',
      description: 'Delete this evidence? This cannot be undone.',
      onConfirm: async () => {
        try {
          await axios.delete(`${API}/investigations/${investigationId}/evidence/${evidenceId}`);
          removeEvidence(evidenceId);
          toast.success('Evidence deleted');
        } catch (error) {
          toast.error('Failed to delete evidence');
        }
      },
    });
  };

  const handleUpdateVerification = async (evidenceId, newStatus, e) => {
    e.stopPropagation();
    try {
      await axios.patch(`${API}/investigations/${investigationId}/evidence/${evidenceId}`, {
        verification_status: newStatus,
      });
      updateEvidence(evidenceId, { verificationStatus: newStatus });
      toast.success(`Marked as ${newStatus}`);
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Empty state
  if (evidence.length === 0) {
    return (
      <div 
        className={`h-full flex flex-col items-center justify-center p-8 transition-colors ${isDragging ? 'bg-primary/5' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="max-w-lg text-center">
          <div className={`w-20 h-20 rounded-full border flex items-center justify-center mx-auto mb-6 transition-colors ${
            isDragging ? 'bg-primary/20 border-primary/50' : 'bg-primary/10 border-primary/20'
          }`}>
            <FileBox className={`w-10 h-10 ${isDragging ? 'text-primary' : 'text-primary'}`} />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            {isDragging ? 'Drop File to Upload' : 'Start Building Your Investigation'}
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            Add evidence such as links, screenshots, documents, or OSINT findings.
            Entities and relationships will be extracted automatically.
          </p>

          {/* Quick Ingest Buttons */}
          <div className="flex flex-wrap gap-3 justify-center mb-6">
            <Button
              data-testid="quick-paste-url-btn"
              onClick={() => { setQuickMode('url'); setShowQuickIngest(true); }}
              variant="outline"
              className="border-primary/30 text-primary hover:bg-primary/10"
            >
              <Link2 className="w-4 h-4 mr-2" />
              Paste URL
            </Button>
            <Button
              data-testid="quick-paste-text-btn"
              onClick={() => { setQuickMode('text'); setShowQuickIngest(true); }}
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/5"
            >
              <ClipboardPaste className="w-4 h-4 mr-2" />
              Paste Text
            </Button>
            <Button
              data-testid="quick-upload-btn"
              onClick={() => { setQuickMode('file'); setShowQuickIngest(true); }}
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/5"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload File
            </Button>
          </div>

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
            <DialogContent className="glass-strong border-white/10 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Add Evidence</DialogTitle>
              </DialogHeader>
              <EvidenceForm 
                categories={EVIDENCE_CATEGORIES}
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                newEvidence={newEvidence} 
                setNewEvidence={setNewEvidence} 
                onSubmit={handleAddEvidence}
              />
            </DialogContent>
          </Dialog>

          <div className="mt-10 grid grid-cols-4 gap-3">
            {Object.entries(EVIDENCE_CATEGORIES).slice(0, 8).map(([key, cat]) => (
              <div 
                key={key}
                className="p-3 rounded-sm bg-white/5 border border-white/5 text-center"
              >
                <cat.icon className="w-5 h-5 mx-auto mb-2" style={{ color: cat.color }} />
                <span className="text-[10px] text-slate-400">{cat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
    <div 
      className={`h-full flex flex-col ${isDragging ? 'bg-primary/5' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <FileBox className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-heading font-bold text-white">Evidence</h2>
          <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
            {evidence.length}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {entities.length > 0 && (
            <Button
              variant="outline"
              onClick={onNavigateToEntities}
              data-testid="evidence-view-entities-button"
              className="border-white/10 text-slate-300 hover:bg-white/5 text-xs h-8"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
              {entities.length} Entities
            </Button>
          )}
          
          {/* Quick Actions */}
          <Button
            onClick={() => { setQuickMode('url'); setShowQuickIngest(true); }}
            data-testid="evidence-quick-url-button"
            variant="outline"
            size="sm"
            className="border-primary/30 text-primary hover:bg-primary/10 text-xs h-8"
          >
            <Link2 className="w-3 h-3 mr-1" />
            URL
          </Button>
          
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-evidence-btn"
                className="bg-primary hover:bg-primary/90 text-white text-xs h-8 rounded-sm"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Add
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-strong border-white/10 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-heading">Add Evidence</DialogTitle>
              </DialogHeader>
              <EvidenceForm 
                categories={EVIDENCE_CATEGORIES}
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                newEvidence={newEvidence} 
                setNewEvidence={setNewEvidence} 
                onSubmit={handleAddEvidence}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Evidence List */}
        <div className={`flex-1 overflow-y-auto p-4 ${showDetectedPanel ? 'border-r border-white/5' : ''}`}>
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
                              {linkedEntities.length} linked
                            </span>
                          )}
                          {/* Verification status badge with cycle button */}
                          {(() => {
                            const status = item.verificationStatus || 'unverified';
                            const statusStyles = {
                              verified: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
                              unverified: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
                              disputed: 'bg-red-500/10 text-red-400 border-red-500/20',
                            };
                            const nextStatus = { verified: 'disputed', unverified: 'verified', disputed: 'unverified' };
                            return (
                              <button
                                data-testid={`evidence-status-button-${item.id}`}
                                onClick={(e) => handleUpdateVerification(item.id, nextStatus[status], e)}
                                className={`text-[10px] px-2 py-0.5 rounded-sm border ${statusStyles[status]} hover:opacity-80 transition-opacity`}
                                title="Click to cycle status"
                              >
                                {status}
                              </button>
                            );
                          })()}
                          {/* Tags display */}
                          {(item.tags || []).map(tag => (
                            <span key={tag} className="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-sm">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <ChevronRight className={`w-4 h-4 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                        <Button
                          variant="ghost"
                          size="sm"
                          data-testid={`evidence-delete-button-${item.id}`}
                          onClick={(e) => handleDeleteEvidence(item.id, e)}
                          className="h-7 w-7 p-0 text-slate-500 hover:text-red-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded: Provenance Chain + Extract Entities */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-2 border-t border-white/5 bg-white/[0.02] space-y-3">
                      {/* Evidence provenance chain */}
                      {linkedEntities.length > 0 && (
                        <div>
                          <span className="text-xs text-cyan-500/80 uppercase tracking-wider font-semibold">Evidence Chain</span>
                          <div className="mt-2 space-y-1">
                            {linkedEntities.map(le => (
                              <div key={le.id} className="flex items-center gap-2 text-xs bg-white/[0.03] border border-white/5 rounded-sm px-2.5 py-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                                <span className="text-slate-300 font-mono">{le.value}</span>
                                <Badge variant="secondary" className="bg-white/5 text-slate-500 border-0 text-[9px] ml-auto">{le.kind}</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* Notes */}
                      {item.notes && (
                        <div>
                          <span className="text-xs text-slate-500 uppercase tracking-wider">Notes</span>
                          <p className="mt-1 text-xs text-slate-400 bg-white/[0.03] rounded-sm p-2 border border-white/5">{item.notes}</p>
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500 uppercase tracking-wider">
                          Extract entities from this evidence
                        </span>
                        <Button
                          data-testid={`evidence-detect-indicators-button-${item.id}`}
                          onClick={async () => {
                            // Run extraction on this evidence
                            try {
                              const contentToExtract = `${item.sourceUrl || ''} ${item.content || ''} ${item.notes || ''}`;
                              const response = await axios.post(`${API}/extract/entities`, {
                                text: contentToExtract,
                                source_evidence_id: item.id
                              });
                              
                              if (response.data.entities?.length > 0) {
                                setDetectedEntities(response.data.entities);
                                setProcessingEvidence(item.id);
                                setShowDetectedPanel(true);
                                toast.success(`Found ${response.data.entities.length} indicators`);
                              } else {
                                toast.info('No indicators detected');
                              }
                            } catch (error) {
                              toast.error('Failed to extract entities');
                            }
                          }}
                          className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 text-xs h-8"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1.5" />
                          Detect Indicators
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Detected Entities Panel */}
        {showDetectedPanel && detectedEntities.length > 0 && (
          <div className="w-80 bg-black/30 border-l border-white/5 flex flex-col">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-white">Detected Indicators</h3>
                <Badge className="bg-amber-500/10 text-amber-400 border-0 text-xs">
                  {detectedEntities.length}
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                data-testid="evidence-close-detected-panel-button"
                onClick={() => {
                  setShowDetectedPanel(false);
                  setDetectedEntities([]);
                }}
                className="h-6 w-6 p-0 text-slate-500 hover:text-white"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              <div className="space-y-2">
                {detectedEntities.map((entity, idx) => {
                  const iconConfig = ENTITY_TYPE_ICONS[entity.type] || { icon: Hash, color: '#94a3b8' };
                  return (
                    <div 
                      key={idx}
                      className="bg-black/40 border border-white/10 rounded-sm p-3 hover:border-amber-500/30 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div 
                          className="w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${iconConfig.color}15`, border: `1px solid ${iconConfig.color}30` }}
                        >
                          <iconConfig.icon className="w-4 h-4" style={{ color: iconConfig.color }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-slate-500 uppercase">{entity.label}</p>
                          <p className="text-sm text-white font-mono truncate">{entity.value}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-slate-500">
                              {Math.round(entity.confidence * 100)}% conf
                            </span>
                            {entity.risk_score > 0.5 && (
                              <Badge className="bg-red-500/10 text-red-400 border-0 text-[10px] h-4">
                                High Risk
                              </Badge>
                            )}
                          </div>
                        </div>
                        <Button
                          size="sm"
                          data-testid={`detected-entity-add-button-${idx}`}
                          onClick={() => handleAddDetectedEntity(entity)}
                          className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-0 h-7 px-2"
                        >
                          <Plus className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="p-3 border-t border-white/5">
              <Button
                data-testid="detected-entity-add-all-button"
                onClick={handleAddAllDetected}
                className="w-full bg-amber-500 hover:bg-amber-600 text-black text-xs h-9"
              >
                <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                Add All ({detectedEntities.length})
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Quick Ingest Dialog */}
      <Dialog open={showQuickIngest} onOpenChange={setShowQuickIngest}>
        <DialogContent className="glass-strong border-white/10 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-heading flex items-center gap-2">
              {quickMode === 'url' && <><Link2 className="w-5 h-5 text-primary" /> Quick URL Ingest</>}
              {quickMode === 'text' && <><ClipboardPaste className="w-5 h-5 text-primary" /> Quick Text Ingest</>}
              {quickMode === 'file' && <><Upload className="w-5 h-5 text-primary" /> Upload File</>}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            {/* Mode Tabs */}
            <div className="flex border border-white/10 rounded-sm overflow-hidden">
              {[
                { key: 'url', label: 'URL', icon: Link2 },
                { key: 'text', label: 'Text', icon: ClipboardPaste },
                { key: 'file', label: 'File', icon: Upload }
              ].map(mode => (
                <button
                  key={mode.key}
                  data-testid={`quick-ingest-mode-${mode.key}`}
                  onClick={() => setQuickMode(mode.key)}
                  className={`flex-1 px-3 py-2 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    quickMode === mode.key
                      ? 'bg-primary text-white'
                      : 'bg-transparent text-slate-400 hover:text-white'
                  }`}
                >
                  <mode.icon className="w-3.5 h-3.5" />
                  {mode.label}
                </button>
              ))}
            </div>

            {quickMode === 'url' && (
              <>
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">URL</Label>
                  <Input
                    data-testid="quick-url-input"
                    value={quickUrl}
                    onChange={(e) => setQuickUrl(e.target.value)}
                    placeholder="https://example.com/page"
                    className="mt-2 bg-black/50 border-white/10 text-white"
                  />
                </div>
                <p className="text-xs text-slate-500">
                  The URL will be fetched and parsed. Entities will be automatically extracted.
                </p>
                <Button
                  data-testid="quick-url-submit-button"
                  onClick={handleQuickUrlIngest}
                  disabled={quickLoading || !quickUrl.trim()}
                  className="w-full bg-primary hover:bg-primary/90 text-white"
                >
                  {quickLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Link2 className="w-4 h-4 mr-2" />}
                  Ingest URL
                </Button>
              </>
            )}

            {quickMode === 'text' && (
              <>
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Title (Optional)</Label>
                  <Input
                    data-testid="quick-text-title-input"
                    value={quickTitle}
                    onChange={(e) => setQuickTitle(e.target.value)}
                    placeholder="Evidence title"
                    className="mt-2 bg-black/50 border-white/10 text-white"
                  />
                </div>
                <div>
                  <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Raw Text</Label>
                  <textarea
                    data-testid="quick-text-input"
                    value={quickText}
                    onChange={(e) => setQuickText(e.target.value)}
                    placeholder="Paste raw text, logs, chat messages, or any content..."
                    className="mt-2 w-full bg-black/50 border border-white/10 text-white rounded-sm px-3 py-2 min-h-[150px] text-sm font-mono"
                  />
                </div>
                <Button
                  data-testid="quick-text-submit-button"
                  onClick={handleQuickTextIngest}
                  disabled={quickLoading || !quickText.trim()}
                  className="w-full bg-primary hover:bg-primary/90 text-white"
                >
                  {quickLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ClipboardPaste className="w-4 h-4 mr-2" />}
                  Ingest Text
                </Button>
              </>
            )}

            {quickMode === 'file' && (
              <>
                <div 
                  data-testid="quick-file-dropzone"
                  className="border-2 border-dashed border-white/20 rounded-sm p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
                  onClick={() => document.getElementById('file-upload').click()}
                >
                  <Upload className="w-10 h-10 text-slate-500 mx-auto mb-3" />
                  <p className="text-sm text-slate-300 mb-1">Click to upload or drag and drop</p>
                  <p className="text-xs text-slate-500">PDF, Images, Documents (max 10MB)</p>
                  <input
                    id="file-upload"
                    data-testid="quick-file-input"
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        handleFileUpload(e.target.files[0]);
                      }
                    }}
                    accept=".pdf,.png,.jpg,.jpeg,.gif,.txt,.log,.csv,.doc,.docx"
                  />
                </div>
                <p className="text-xs text-slate-500">
                  Files will be processed for text extraction. OCR will be applied to images.
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
    <ConfirmDialog {...dialogProps} />
    </>
  );
};

// Evidence Form Component with Categories
const EvidenceForm = ({ categories, selectedCategory, setSelectedCategory, newEvidence, setNewEvidence, onSubmit }) => {
  const currentCategory = categories[selectedCategory];
  
  return (
    <div className="space-y-4 mt-4">
      {/* Category Selection */}
      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider mb-3 block">
          Evidence Category
        </Label>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(categories).map(([key, cat]) => (
            <button
              key={key}
              data-testid={`evidence-category-button-${key}`}
              onClick={() => {
                setSelectedCategory(key);
                setNewEvidence({ ...newEvidence, evidence_type: cat.types[0].value });
              }}
              className={`p-3 rounded-sm border text-center transition-colors duration-200 ${
                selectedCategory === key
                  ? 'bg-white/10 border-primary/50'
                  : 'bg-white/5 border-white/10 hover:border-white/20'
              }`}
            >
              <cat.icon 
                className="w-5 h-5 mx-auto mb-1" 
                style={{ color: selectedCategory === key ? cat.color : '#94a3b8' }} 
              />
              <span className={`text-[10px] ${selectedCategory === key ? 'text-white' : 'text-slate-400'}`}>
                {cat.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Evidence Type */}
      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Evidence Type</Label>
        <Select 
          value={newEvidence.evidence_type} 
          onValueChange={(value) => setNewEvidence({ ...newEvidence, evidence_type: value })}
        >
          <SelectTrigger data-testid="evidence-form-type-select" className="mt-2 bg-black/50 border-white/10 text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#0a0a0a] border-white/10 text-white">
            {currentCategory?.types.map(type => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Title</Label>
        <Input
          data-testid="evidence-form-title-input"
          value={newEvidence.title}
          onChange={(e) => setNewEvidence({ ...newEvidence, title: e.target.value })}
          className="mt-2 bg-black/50 border-white/10 text-white"
          placeholder="Evidence title"
        />
      </div>

      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Source URL</Label>
        <Input
          data-testid="evidence-form-source-url-input"
          value={newEvidence.source_url}
          onChange={(e) => setNewEvidence({ ...newEvidence, source_url: e.target.value })}
          className="mt-2 bg-black/50 border-white/10 text-white"
          placeholder="https://..."
        />
      </div>

      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Content</Label>
        <textarea
          data-testid="evidence-form-content-input"
          value={newEvidence.content}
          onChange={(e) => setNewEvidence({ ...newEvidence, content: e.target.value })}
          className="mt-2 w-full bg-black/50 border border-white/10 text-white rounded-sm px-3 py-2 min-h-[100px] text-sm"
          placeholder="Describe the evidence or paste content..."
        />
      </div>

      <div>
        <Label className="text-xs font-semibold text-cyan-500/80 uppercase tracking-wider">Notes</Label>
        <Input
          data-testid="evidence-form-notes-input"
          value={newEvidence.notes}
          onChange={(e) => setNewEvidence({ ...newEvidence, notes: e.target.value })}
          className="mt-2 bg-black/50 border-white/10 text-white"
          placeholder="Additional notes"
        />
      </div>

      <Button
        data-testid="evidence-form-submit-button"
        onClick={onSubmit}
        className="w-full bg-primary hover:bg-primary/90 text-white rounded-sm shadow-glow h-10"
      >
        <Plus className="w-4 h-4 mr-2" />
        Add Evidence
      </Button>
    </div>
  );
};

export default EvidenceWorkspace;
