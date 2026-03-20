import { create } from 'zustand';

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
  
  // Core data
  entities: [],
  relationships: [],
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
  setInvestigation: (investigation) => set({ investigation }),
  
  setEntities: (entities) => set({ entities }),
  
  addEntity: (entity) => set((state) => {
    const timelineEvent = createTimelineEvent(
      'ENTITY_ADDED',
      `Added ${entity.kind}: ${entity.value}`,
      { entityIds: [entity.id] },
      { source: 'manual', confidence: entity.confidence },
    );
    return {
      entities: [...state.entities, entity],
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  updateEntity: (id, updates) => set((state) => ({
    entities: state.entities.map(e => e.id === id ? { ...e, ...updates } : e),
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
      relationships: state.relationships.filter(r => r.fromId !== id && r.toId !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setRelationships: (relationships) => set({ relationships }),
  
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
  
  acceptAISuggestion: (suggestionId) => set((state) => {
    const suggestion = state.aiSuggestions.find(s => s.id === suggestionId);
    if (!suggestion) return state;
    
    let newState = { ...state };
    const timelineEvent = createTimelineEvent(
      'AI_SUGGESTION_ACCEPTED',
      `Accepted AI suggestion: ${suggestion.title}`,
      {},
      { suggestionId, type: suggestion.type },
    );
    
    // Execute actions
    suggestion.actions?.forEach(action => {
      if (action.kind === 'ADD_ENTITY') {
        const newEntity = {
          id: `ent-${Date.now()}-${Math.random()}`,
          ...action.payload,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        newState.entities = [...newState.entities, newEntity];
      } else if (action.kind === 'ADD_EDGE') {
        const newEdge = {
          id: `edge-${Date.now()}-${Math.random()}`,
          ...action.payload,
          createdAt: new Date().toISOString(),
        };
        newState.relationships = [...newState.relationships, newEdge];
      }
    });
    
    return {
      ...newState,
      aiSuggestions: state.aiSuggestions.map(s => 
        s.id === suggestionId ? { ...s, status: 'accepted' } : s
      ),
      timeline: [timelineEvent, ...newState.timeline],
    };
  }),
  
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
    entities: [],
    relationships: [],
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
