import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import InvestigationWorkspace from './InvestigationWorkspace';
import axios, { API, API_KEY, BACKEND_URL } from '../config/api';
import useInvestigationStore from '../store/investigationStore';
import { toast } from 'sonner';

const mockNavigate = jest.fn();
const mockSetInvestigation = jest.fn();
const mockSetEntities = jest.fn();
const mockSetRelationships = jest.fn();
const mockSetTimeline = jest.fn();
const mockSetEvidence = jest.fn();
const mockClearInvestigation = jest.fn();

jest.mock('react-router-dom', () => ({
  useParams: () => ({ id: 'inv-123' }),
  useNavigate: () => mockNavigate,
}));

jest.mock('lucide-react', () => {
  const Icon = (props) => <svg data-testid="icon" {...props} />;
  return {
    ArrowLeft: Icon,
    FileBox: Icon,
    Users: Icon,
    Network: Icon,
    Clock: Icon,
    Sparkles: Icon,
    Search: Icon,
    Settings: Icon,
    Lightbulb: Icon,
    Brain: Icon,
    Download: Icon,
    ChevronDown: Icon,
  };
});

jest.mock('../config/api', () => {
  const mockGet = jest.fn();
  return {
    __esModule: true,
    default: { get: mockGet },
    API: 'http://localhost:8001/api',
    API_KEY: 'test-api-key',
    BACKEND_URL: 'http://localhost:8001',
  };
});

jest.mock('../store/investigationStore', () => jest.fn());
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));

jest.mock('../components/workspace/EvidenceWorkspace', () => () => <div>Evidence Workspace</div>);
jest.mock('../components/workspace/EntitiesWorkspace', () => () => <div>Entities Workspace</div>);
jest.mock('../components/workspace/GraphView', () => () => <div>Graph Workspace</div>);
jest.mock('../components/workspace/TimelineWorkspace', () => () => <div>Timeline Workspace</div>);
jest.mock('../components/workspace/AISuggestionsWorkspace', () => () => <div>AI Suggestions Workspace</div>);
jest.mock('../components/workspace/LeadsWorkspace', () => () => <div>Leads Workspace</div>);
jest.mock('../components/workspace/AIChatWorkspace', () => () => <div>AI Chat Workspace</div>);

describe('InvestigationWorkspace', () => {
  const mockStoreState = {
    investigation: { name: 'Case Alpha', case_id: 'CA-1' },
    entities: [],
    relationships: [],
    timeline: [],
    evidence: [],
    setInvestigation: mockSetInvestigation,
    setEntities: mockSetEntities,
    setRelationships: mockSetRelationships,
    setTimeline: mockSetTimeline,
    setEvidence: mockSetEvidence,
    clearInvestigation: mockClearInvestigation,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useInvestigationStore.mockReturnValue(mockStoreState);
    global.fetch = jest.fn();
  });

  it('shows loading initially and then renders evidence workspace after successful load', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [{ id: 'e1', entity_type: 'person', value: 'John', created_at: '2026-01-01' }] })
      .mockResolvedValueOnce({ data: [{ id: 'r1', source_entity_id: 'e1', target_entity_id: 'e2', relationship_type: 'knows', created_at: '2026-01-01' }] })
      .mockResolvedValueOnce({ data: [{ id: 't1', timestamp: '2026-01-01', event_type: 'created', description: 'Created', metadata: {} }] })
      .mockResolvedValueOnce({ data: [{ id: 'ev1', evidence_type: 'note', content: 'test', collected_at: '2026-01-01' }] });

    render(<InvestigationWorkspace />);

    expect(screen.getByText(/Loading investigation/i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    expect(mockSetInvestigation).toHaveBeenCalledWith({ name: 'Case Alpha', case_id: 'CA-1' });
    expect(mockSetEntities).toHaveBeenCalledTimes(1);
    expect(mockSetRelationships).toHaveBeenCalledTimes(1);
    expect(mockSetTimeline).toHaveBeenCalledTimes(1);
    expect(mockSetEvidence).toHaveBeenCalledTimes(1);
  });

  it('handles load failure with toast and navigation home', async () => {
    axios.get.mockRejectedValue(new Error('network fail'));

    render(<InvestigationWorkspace />);

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to load investigation'));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('switches tabs when tab buttons are clicked', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    render(<InvestigationWorkspace />);

    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('tab-entities'));
    expect(screen.getByText('Entities Workspace')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('tab-graph'));
    expect(screen.getByText('Graph Workspace')).toBeInTheDocument();
  });

  it('opens export menu and triggers successful export download flow', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    const mockBlob = new Blob(['{}'], { type: 'application/json' });
    fetch.mockResolvedValue({ ok: true, blob: async () => mockBlob });

    const createObjectURLSpy = jest.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
    const revokeObjectURLSpy = jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    render(<InvestigationWorkspace />);

    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('export-btn'));
    fireEvent.click(screen.getByText('JSON (full data)'));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(`${BACKEND_URL}/api/investigations/inv-123/export/json`, {
        headers: { 'x-api-key': API_KEY },
      });
      expect(toast.success).toHaveBeenCalledWith('JSON export downloaded');
    });

    createObjectURLSpy.mockRestore();
    revokeObjectURLSpy.mockRestore();
  });

  it('shows error toast when export fails', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    fetch.mockResolvedValue({ ok: false });

    render(<InvestigationWorkspace />);

    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('export-btn'));
    fireEvent.click(screen.getByText('JSON (full data)'));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Export failed'));
  });

  it('clears investigation state on unmount', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    const { unmount } = render(<InvestigationWorkspace />);
    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    unmount();
    expect(mockClearInvestigation).toHaveBeenCalled();
  });

  it('calls backend endpoints for initial load', async () => {
    axios.get
      .mockResolvedValueOnce({ data: { name: 'Case Alpha', case_id: 'CA-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    render(<InvestigationWorkspace />);

    await waitFor(() => expect(screen.getByText('Evidence Workspace')).toBeInTheDocument());

    expect(axios.get).toHaveBeenNthCalledWith(1, `${API}/investigations/inv-123`);
    expect(axios.get).toHaveBeenNthCalledWith(2, `${API}/investigations/inv-123/entities`);
    expect(axios.get).toHaveBeenNthCalledWith(3, `${API}/investigations/inv-123/relationships`);
    expect(axios.get).toHaveBeenNthCalledWith(4, `${API}/investigations/inv-123/timeline`);
    expect(axios.get).toHaveBeenNthCalledWith(5, `${API}/investigations/inv-123/evidence`);
  });
});
