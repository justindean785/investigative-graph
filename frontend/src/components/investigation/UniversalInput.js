import React, { useState, useEffect, useCallback } from 'react';
import { Zap, Pause, Play, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';

const UniversalInput = ({ investigationId, onInvestigationStarted }) => {
  const [input, setInput] = useState('');
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [status, setStatus] = useState(null);

  const checkStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/auto-status`);
      setStatus(response.data);
      setIsInvestigating(response.data.status === 'running');
    } catch (error) {
      console.error('Failed to check status:', error);
    }
  }, [investigationId]);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, [checkStatus]);

  const handleInvestigate = async () => {
    if (!input.trim()) {
      toast.error('Please enter something to investigate');
      return;
    }

    try {
      setIsInvestigating(true);
      const response = await axios.post(
        `${API}/investigations/${investigationId}/auto-investigate`,
        {
          seed_input: input,
          max_depth: 5,
          max_entities: 100,
          confidence_threshold: 0.3
        }
      );

      toast.success('Investigation started!');
      setInput('');
      
      if (onInvestigationStarted) {
        onInvestigationStarted(response.data);
      }
    } catch (error) {
      console.error('Failed to start investigation:', error);
      toast.error(error.response?.data?.detail || 'Failed to start investigation');
      setIsInvestigating(false);
    }
  };

  const handlePause = async () => {
    try {
      await axios.post(`${API}/investigations/${investigationId}/pause`);
      toast.success('Investigation paused');
      setIsInvestigating(false);
    } catch (error) {
      toast.error('Failed to pause investigation');
    }
  };

  const handleResume = async () => {
    try {
      await axios.post(`${API}/investigations/${investigationId}/resume`);
      toast.success('Investigation resumed');
      setIsInvestigating(true);
    } catch (error) {
      toast.error('Failed to resume investigation');
    }
  };

  return (
    <div className="p-4 border-b border-white/5 bg-black/30">
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isInvestigating}
            placeholder="Paste anything — phone numbers, emails, usernames, breach data, raw text... The AI will extract entities and investigate automatically."
            className="flex-1 bg-black/50 border border-white/10 rounded-sm px-4 py-3 text-sm text-white placeholder:text-slate-500 resize-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 disabled:opacity-50"
            rows={3}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !isInvestigating) {
                handleInvestigate();
              }
            }}
          />
          
          <div className="flex flex-col gap-2">
            {!isInvestigating ? (
              <Button
                onClick={handleInvestigate}
                disabled={!input.trim() || isInvestigating}
                className="bg-primary hover:bg-primary/90 text-white px-6 h-full shadow-glow"
              >
                <Zap className="w-4 h-4 mr-2" />
                Investigate
              </Button>
            ) : (
              <>
                <Button
                  onClick={handlePause}
                  className="bg-orange-500 hover:bg-orange-600 text-white px-6"
                >
                  <Pause className="w-4 h-4 mr-2" />
                  Pause
                </Button>
                <div className="flex items-center justify-center gap-2 text-xs text-primary">
                  <Activity className="w-3 h-3 animate-pulse" />
                  <span>Working...</span>
                </div>
              </>
            )}
          </div>
        </div>
        
        {status && status.status !== 'not_started' && (
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-4">
              <span>Processed: <span className="text-white">{status.processed_count || 0}</span></span>
              <span>Discovered: <span className="text-primary">{status.entities_discovered || 0}</span></span>
              <span>Depth: <span className="text-cyan-400">{status.current_depth || 0}/{status.max_depth || 5}</span></span>
              {status.queue_size > 0 && (
                <span>Queue: <span className="text-amber-400">{status.queue_size}</span></span>
              )}
            </div>
            
            {status.status === 'paused' && (
              <Button
                onClick={handleResume}
                variant="ghost"
                className="text-primary hover:text-primary/80 h-6 px-2 text-xs"
              >
                <Play className="w-3 h-3 mr-1" />
                Resume
              </Button>
            )}
          </div>
        )}
        
        <p className="mt-2 text-[10px] text-slate-500">
          Press <kbd className="px-1 py-0.5 bg-white/5 rounded text-[9px]">Ctrl+Enter</kbd> to start investigation
        </p>
      </div>
    </div>
  );
};

export default UniversalInput;
