import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, Loader2, Trash2, Bot, User, Sparkles, Brain, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios, { API } from '../../config/api';
import useInvestigationStore from '../../store/investigationStore';

const AIChatWorkspace = ({ investigationId, onNavigateToEvidence }) => {
  const { entities, relationships, evidence } = useInvestigationStore();
  
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    loadChatHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investigationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChatHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await axios.get(`${API}/investigations/${investigationId}/chat/history`);
      if (response.data.messages?.length > 0) {
        setMessages(response.data.messages);
        // Get session ID from last message
        const lastMsg = response.data.messages[response.data.messages.length - 1];
        if (lastMsg.session_id) {
          setSessionId(lastMsg.session_id);
        }
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const sendMessage = async () => {
    const message = inputValue.trim();
    if (!message || loading) return;

    setInputValue('');
    setLoading(true);

    // Add user message to UI immediately
    const userMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await axios.post(`${API}/investigations/${investigationId}/ai/chat`, {
        message,
        session_id: sessionId
      });

      if (response.data.success) {
        // Update session ID if new
        if (response.data.session_id && !sessionId) {
          setSessionId(response.data.session_id);
        }

        // Add assistant message
        const assistantMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: response.data.message,
          timestamp: response.data.timestamp
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      toast.error('Failed to send message');
      // Remove the user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      setInputValue(message); // Restore input
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const clearHistory = async () => {
    if (!window.confirm('Clear all chat history for this investigation?')) return;

    try {
      await axios.delete(`${API}/investigations/${investigationId}/chat/clear`);
      setMessages([]);
      setSessionId(null);
      toast.success('Chat history cleared');
    } catch (error) {
      toast.error('Failed to clear history');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestedQuestions = [
    "What entities are most connected in this investigation?",
    "Are there any suspicious patterns I should investigate?",
    "Summarize the current state of this investigation.",
    "What are the next recommended investigative steps?",
    "Identify potential connections between high-risk entities."
  ];

  // Empty state - not enough data
  if (entities.length === 0 && evidence.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-20 h-20 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
            <Brain className="w-10 h-10 text-emerald-400" />
          </div>
          
          <h2 className="text-2xl font-heading font-bold text-white mb-3">
            AI Investigation Analyst
          </h2>
          
          <p className="text-slate-400 mb-8 leading-relaxed">
            Chat with your AI analyst to get insights about your investigation. 
            Ask questions about entities, relationships, patterns, and get recommendations for next steps.
            Add evidence and entities first to enable AI analysis.
          </p>

          <Button 
            onClick={onNavigateToEvidence}
            className="bg-emerald-500 hover:bg-emerald-600 text-white"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Start Building Your Case
          </Button>

          <div className="mt-8 text-left p-4 bg-white/5 rounded-sm border border-white/10">
            <p className="text-xs text-emerald-400/80 uppercase tracking-wider mb-3 font-semibold">
              Sample Questions
            </p>
            <div className="space-y-2">
              {suggestedQuestions.slice(0, 3).map((q, i) => (
                <p key={i} className="text-xs text-slate-400 flex items-start gap-2">
                  <MessageSquare className="w-3 h-3 mt-0.5 text-emerald-500/50" />
                  {q}
                </p>
              ))}
            </div>
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
          <Brain className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-heading font-bold text-white">AI Analyst</h2>
          <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-0 text-xs">
            Gemini Flash
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadChatHistory}
            className="border-white/10 text-slate-400 hover:bg-white/5 text-xs h-8"
          >
            <RefreshCw className="w-3 h-3 mr-1.5" />
            Refresh
          </Button>
          {messages.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={clearHistory}
              className="border-white/10 text-slate-400 hover:bg-white/5 hover:text-red-400 text-xs h-8"
            >
              <Trash2 className="w-3 h-3 mr-1.5" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Context Banner */}
      <div className="px-4 py-3 border-b border-white/5 bg-emerald-500/5">
        <div className="flex items-center gap-4 text-xs">
          <span className="text-slate-400">
            Context: <span className="text-emerald-400 font-medium">{entities.length}</span> entities
          </span>
          <span className="text-slate-400">
            <span className="text-emerald-400 font-medium">{relationships.length}</span> connections
          </span>
          <span className="text-slate-400">
            <span className="text-emerald-400 font-medium">{evidence.length}</span> evidence items
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {loadingHistory ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <Bot className="w-12 h-12 text-emerald-400/50 mb-4" />
            <p className="text-slate-400 mb-6">Start a conversation with your AI analyst</p>
            
            <div className="w-full max-w-md space-y-2">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Suggested questions</p>
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInputValue(question);
                    inputRef.current?.focus();
                  }}
                  className="w-full text-left px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/5 hover:border-emerald-500/30 rounded-sm text-sm text-slate-300 transition-all"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((msg, idx) => (
              <div
                key={msg.id || idx}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-sm bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-emerald-400" />
                  </div>
                )}
                
                <div
                  className={`max-w-[80%] rounded-sm px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-primary/20 border border-primary/30 text-white'
                      : 'bg-white/5 border border-white/10 text-slate-200'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-2">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-sm bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-primary" />
                  </div>
                )}
              </div>
            ))}
            
            {loading && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-sm bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="bg-white/5 border border-white/10 rounded-sm px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                    <span className="text-sm text-slate-400">Analyzing...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-white/5 bg-black/30">
        <div className="max-w-3xl mx-auto flex gap-3">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your investigation..."
            disabled={loading}
            rows={1}
            className="flex-1 bg-black/50 border border-white/10 rounded-sm px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 resize-none min-h-[48px] max-h-32"
            style={{ height: 'auto' }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
            }}
          />
          <Button
            onClick={sendMessage}
            disabled={loading || !inputValue.trim()}
            className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 h-12 rounded-sm"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
        <p className="text-[10px] text-slate-600 text-center mt-2">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

export default AIChatWorkspace;
