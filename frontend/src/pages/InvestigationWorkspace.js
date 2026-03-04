import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Network, List, Clock, FileBox, Sparkles, Settings, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { API } from '../App';

import EntitiesTab from '../components/EntitiesTab';
import GraphTab from '../components/GraphTab';
import TimelineTab from '../components/TimelineTab';
import EvidenceTab from '../components/EvidenceTab';
import AISuggestionsTab from '../components/AISuggestionsTab';

const InvestigationWorkspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [investigation, setInvestigation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('graph');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    fetchInvestigation();
  }, [id]);

  const fetchInvestigation = async () => {
    try {
      const response = await axios.get(`${API}/investigations/${id}`);
      setInvestigation(response.data);
    } catch (error) {
      console.error('Failed to fetch investigation:', error);
      toast.error('Failed to load investigation');
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const triggerRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const deleteInvestigation = async () => {
    if (!window.confirm('Are you sure you want to delete this investigation? This action cannot be undone.')) {
      return;
    }

    try {
      await axios.delete(`${API}/investigations/${id}`);
      toast.success('Investigation deleted successfully');
      navigate('/');
    } catch (error) {
      console.error('Failed to delete investigation:', error);
      toast.error('Failed to delete investigation');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a1628] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
          <p className="mt-4 text-[#94a3b8]">Loading investigation...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a1628] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#00d9ff]/20 glass">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              data-testid="back-to-dashboard-btn"
              variant="ghost"
              onClick={() => navigate('/')}
              className="text-[#00d9ff] hover:text-white hover:bg-[#00d9ff]/10"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-[#00d9ff]">{investigation?.name}</h1>
              <p className="text-xs text-[#94a3b8] font-mono mt-1">{investigation?.case_id}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              className="text-[#94a3b8] hover:text-white hover:bg-[#00d9ff]/10"
            >
              <Settings className="w-4 h-4" />
            </Button>
            <Button
              data-testid="delete-investigation-btn"
              variant="ghost"
              onClick={deleteInvestigation}
              className="text-[#ff3b30] hover:text-white hover:bg-[#ff3b30]/10"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <TabsList className="bg-[#0d1b2a]/80 border border-[#00d9ff]/20 p-1 mb-6 inline-flex w-fit">
            <TabsTrigger
              value="graph"
              data-testid="graph-tab"
              className="data-[state=active]:bg-[#00d9ff] data-[state=active]:text-black text-[#94a3b8] hover:text-white transition-colors px-6"
            >
              <Network className="w-4 h-4 mr-2" />
              Graph
            </TabsTrigger>
            <TabsTrigger
              value="entities"
              data-testid="entities-tab"
              className="data-[state=active]:bg-[#00d9ff] data-[state=active]:text-black text-[#94a3b8] hover:text-white transition-colors px-6"
            >
              <List className="w-4 h-4 mr-2" />
              Entities
            </TabsTrigger>
            <TabsTrigger
              value="timeline"
              data-testid="timeline-tab"
              className="data-[state=active]:bg-[#00d9ff] data-[state=active]:text-black text-[#94a3b8] hover:text-white transition-colors px-6"
            >
              <Clock className="w-4 h-4 mr-2" />
              Timeline
            </TabsTrigger>
            <TabsTrigger
              value="evidence"
              data-testid="evidence-tab"
              className="data-[state=active]:bg-[#00d9ff] data-[state=active]:text-black text-[#94a3b8] hover:text-white transition-colors px-6"
            >
              <FileBox className="w-4 h-4 mr-2" />
              Evidence
            </TabsTrigger>
            <TabsTrigger
              value="ai"
              data-testid="ai-tab"
              className="data-[state=active]:bg-[#00d9ff] data-[state=active]:text-black text-[#94a3b8] hover:text-white transition-colors px-6"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              AI Suggestions
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-hidden">
            <TabsContent value="graph" className="h-full mt-0">
              <GraphTab investigationId={id} refreshTrigger={refreshTrigger} onRefresh={triggerRefresh} />
            </TabsContent>

            <TabsContent value="entities" className="h-full mt-0">
              <EntitiesTab investigationId={id} refreshTrigger={refreshTrigger} onRefresh={triggerRefresh} />
            </TabsContent>

            <TabsContent value="timeline" className="h-full mt-0">
              <TimelineTab investigationId={id} refreshTrigger={refreshTrigger} />
            </TabsContent>

            <TabsContent value="evidence" className="h-full mt-0">
              <EvidenceTab investigationId={id} refreshTrigger={refreshTrigger} onRefresh={triggerRefresh} />
            </TabsContent>

            <TabsContent value="ai" className="h-full mt-0">
              <AISuggestionsTab investigationId={id} refreshTrigger={refreshTrigger} onRefresh={triggerRefresh} />
            </TabsContent>
          </div>
        </Tabs>
      </main>
    </div>
  );
};

export default InvestigationWorkspace;
