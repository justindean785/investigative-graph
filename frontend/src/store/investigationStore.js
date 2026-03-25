import { create } from 'zustand';
import axios, { API } from '../config/api';

const api = {
  post: (path, payload) => axios.post(`${API}${path}`, payload),
};

// Helper to create timeline events, reducing repetition across store actions
function createTimelineEvent(type, summary, refs = {}, meta = {}) {
  return {
    id: `evt-${Date.now()}`,
    ts: new Date().toISOString(),
    type,
    summary,
    refs: { entityIds: [], evidenceIds: [], edgeIds: [], ...refs },
    meta,
  };
}

const useInvestigationStore = create((set, get) => ({
  // Investigation metadata
  investigation: null,
  currentInvestigationId: null,
  
  // Core data
  entities: [],
  relationships: [],
  nodes: [],
  edges: [],
  evidence: [],
  timeline: [],
  aiSuggestions: [],
  
  // UI state
  ui: {
    selectedEntityId: null,
    selectedEdgeId: null,
    activeTab: 'graph',
    filters: {
      entityKinds: [],
      riskThreshold: 0,
      tags: [],
    },
    graphLayout: {
      positions: {}, // entityId -> {x, y}
    },
  },
  
  // Actions
  setInvestigation: (investigation) => set({
    investigation,
    currentInvestigationId: investigation?.id || null,
  }),
  
  setEntities: (entities) => set({ entities, nodes: entities }),
  
  addEntity: (entity) => set((state) => {
    const timelineEvent = createTimelineEvent(
      'ENTITY_ADDED',
      `Added ${entity.kind}: ${entity.value}`,
      { entityIds: [entity.id] },
      { source: 'manual', confidence: entity.confidence },
    );
    return {
      entities: [...state.entities, entity],
      nodes: [...state.nodes, entity],
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  updateEntity: (id, updates) => set((state) => ({
    entities: state.entities.map(e => e.id === id ? { ...e, ...updates } : e),
    nodes: state.nodes.map(e => e.id === id ? { ...e, ...updates } : e),
  })),
  
  removeEntity: (id) => set((state) => {
    const entity = state.entities.find(e => e.id === id);
    const timelineEvent = createTimelineEvent(
      'ENTITY_REMOVED',
      `Removed ${entity?.kind || 'entity'}: ${entity?.value || ''}`,
      { entityIds: [id] },
    );
    return {
      entities: state.entities.filter(e => e.id !== id),
      nodes: state.nodes.filter(e => e.id !== id),
      relationships: state.relationships.filter(r => r.fromId !== id && r.toId !== id),
      edges: state.edges.filter(r => r.fromId !== id && r.toId !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setRelationships: (relationships) => set({ relationships, edges: relationships }),
  
  addRelationship: (relationship) => set((state) => {
    const fromEntity = state.entities.find(e => e.id === relationship.fromId);
    const toEntity = state.entities.find(e => e.id === relationship.toId);
    const timelineEvent = createTimelineEvent(
      'EDGE_CREATED',
      `Connected ${fromEntity?.label || ''} ${relationship.relType} ${toEntity?.label || ''}`,
      { entityIds: [relationship.fromId, relationship.toId], edgeIds: [relationship.id] },
      { confidence: relationship.confidence },
    );
    return {
      relationships: [...state.relationships, relationship],
      edges: [...state.edges, relationship],
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  removeRelationship: (id) => set((state) => {
    const timelineEvent = createTimelineEvent(
      'EDGE_REMOVED',
      'Removed connection',
      { edgeIds: [id] },
    );
    return {
      relationships: state.relationships.filter(r => r.id !== id),
      edges: state.edges.filter(r => r.id !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setEvidence: (evidence) => set({ evidence }),
  
  addEvidence: (evidenceItem) => set((state) => {
    const timelineEvent = createTimelineEvent(
      'EVIDENCE_ADDED',
      `Added evidence: ${evidenceItem.title}`,
      { 
        entityIds: evidenceItem.linked?.entityIds || [], 
        evidenceIds: [evidenceItem.id], 
        edgeIds: evidenceItem.linked?.edgeIds || [] 
      },
      { type: evidenceItem.type },
    );
    return {
      evidence: [...state.evidence, evidenceItem],
      timeline: [timelineEvent, ...state.timeline],
    };
  }),

  updateEvidence: (id, updates) => set((state) => ({
    evidence: state.evidence.map(e => e.id === id ? { ...e, ...updates } : e),
  })),
  
  removeEvidence: (id) => set((state) => {
    const timelineEvent = createTimelineEvent(
      'EVIDENCE_REMOVED',
      'Removed evidence',
      { evidenceIds: [id] },
    );
    return {
      evidence: state.evidence.filter(e => e.id !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setTimeline: (timeline) => set({ timeline }),
  
  addTimelineEvent: (event) => set((state) => ({
    timeline: [event, ...state.timeline],
  })),
  
  setAISuggestions: (suggestions) => set({ aiSuggestions: suggestions }),
  
  addAISuggestion: (suggestion) => set((state) => ({
    aiSuggestions: [...state.aiSuggestions, suggestion],
  })),
  
  acceptAISuggestion: async (suggestionId) => {
    const suggestion = get().aiSuggestions.find(s => s.id === suggestionId);
    if (!suggestion) return;

    try {
      await api.post(`/investigations/${get().currentInvestigationId}/suggestions/${suggestionId}/accept`);
    } catch (e) {
      console.warn('Backend persist failed, still applying locally', e);
    }

    const suggestionNodes = suggestion.nodes || suggestion.entities || [];
    const suggestionEdges = suggestion.edges || suggestion.relationships || [];

    set((state) => ({
      nodes: [...state.nodes, ...suggestionNodes],
      edges: [...state.edges, ...suggestionEdges],
      entities: [...state.entities, ...suggestionNodes],
      relationships: [...state.relationships, ...suggestionEdges],
      aiSuggestions: state.aiSuggestions.filter(s => s.id !== suggestionId),
    }));
  },
  
  dismissAISuggestion: (suggestionId) => set((state) => ({
    aiSuggestions: state.aiSuggestions.map(s => 
      s.id === suggestionId ? { ...s, status: 'dismissed' } : s
    ),
  })),
  
  // UI Actions
  selectEntity: (entityId) => set((state) => ({
    ui: { ...state.ui, selectedEntityId: entityId },
  })),
  
  selectEdge: (edgeId) => set((state) => ({
    ui: { ...state.ui, selectedEdgeId: edgeId },
  })),
  
  setActiveTab: (tab) => set((state) => ({
    ui: { ...state.ui, activeTab: tab },
  })),
  
  setFilters: (filters) => set((state) => ({
    ui: { ...state.ui, filters: { ...state.ui.filters, ...filters } },
  })),
  
  updateNodePosition: (entityId, position) => set((state) => ({
    ui: {
      ...state.ui,
      graphLayout: {
        ...state.ui.graphLayout,
        positions: {
          ...state.ui.graphLayout.positions,
          [entityId]: position,
        },
      },
    },
  })),
  
  // Clear all data
  clearInvestigation: () => set({
    investigation: null,
    currentInvestigationId: null,
    entities: [],
    relationships: [],
    nodes: [],
    edges: [],
    evidence: [],
    timeline: [],
    aiSuggestions: [],
    ui: {
      selectedEntityId: null,
      selectedEdgeId: null,
      activeTab: 'graph',
      filters: {
        entityKinds: [],
        riskThreshold: 0,
        tags: [],
      },
      graphLayout: {
        positions: {},
      },
    },
  }),
}));

export default useInvestigationStore;
