import { create } from 'zustand';

const useInvestigationStore = create((set, get) => ({
  // Investigation metadata
  investigation: null,
  
  // Core data
  entities: [],
  relationships: [],
  evidence: [],
  timeline: [],
  aiSuggestions: [],
  tasks: [],
  
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
    const newEntities = [...state.entities, entity];
    // Add timeline event
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'ENTITY_ADDED',
      summary: `Added ${entity.kind}: ${entity.value}`,
      refs: { entityIds: [entity.id], evidenceIds: [], edgeIds: [] },
      meta: { source: 'manual', confidence: entity.confidence },
    };
    return {
      entities: newEntities,
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  updateEntity: (id, updates) => set((state) => ({
    entities: state.entities.map(e => e.id === id ? { ...e, ...updates } : e),
  })),
  
  removeEntity: (id) => set((state) => {
    const entity = state.entities.find(e => e.id === id);
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'ENTITY_REMOVED',
      summary: `Removed ${entity?.kind || 'entity'}: ${entity?.value || ''}`,
      refs: { entityIds: [id], evidenceIds: [], edgeIds: [] },
      meta: {},
    };
    return {
      entities: state.entities.filter(e => e.id !== id),
      relationships: state.relationships.filter(r => r.fromId !== id && r.toId !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setRelationships: (relationships) => set({ relationships }),
  
  addRelationship: (relationship) => set((state) => {
    const newRelationships = [...state.relationships, relationship];
    const fromEntity = state.entities.find(e => e.id === relationship.fromId);
    const toEntity = state.entities.find(e => e.id === relationship.toId);
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'EDGE_CREATED',
      summary: `Connected ${fromEntity?.label || ''} ${relationship.relType} ${toEntity?.label || ''}`,
      refs: { entityIds: [relationship.fromId, relationship.toId], evidenceIds: [], edgeIds: [relationship.id] },
      meta: { confidence: relationship.confidence },
    };
    return {
      relationships: newRelationships,
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  removeRelationship: (id) => set((state) => {
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'EDGE_REMOVED',
      summary: 'Removed connection',
      refs: { entityIds: [], evidenceIds: [], edgeIds: [id] },
      meta: {},
    };
    return {
      relationships: state.relationships.filter(r => r.id !== id),
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  setEvidence: (evidence) => set({ evidence }),
  
  addEvidence: (evidenceItem) => set((state) => {
    const newEvidence = [...state.evidence, evidenceItem];
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'EVIDENCE_ADDED',
      summary: `Added evidence: ${evidenceItem.title}`,
      refs: { 
        entityIds: evidenceItem.linked?.entityIds || [], 
        evidenceIds: [evidenceItem.id], 
        edgeIds: evidenceItem.linked?.edgeIds || [] 
      },
      meta: { type: evidenceItem.type },
    };
    return {
      evidence: newEvidence,
      timeline: [timelineEvent, ...state.timeline],
    };
  }),
  
  removeEvidence: (id) => set((state) => {
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'EVIDENCE_REMOVED',
      summary: 'Removed evidence',
      refs: { entityIds: [], evidenceIds: [id], edgeIds: [] },
      meta: {},
    };
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
    const timelineEvent = {
      id: `evt-${Date.now()}`,
      ts: new Date().toISOString(),
      type: 'AI_SUGGESTION_ACCEPTED',
      summary: `Accepted AI suggestion: ${suggestion.title}`,
      refs: { entityIds: [], evidenceIds: [], edgeIds: [] },
      meta: { suggestionId, type: suggestion.type },
    };
    
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
    tasks: [],
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
