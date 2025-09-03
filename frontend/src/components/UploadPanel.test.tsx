import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UploadPanel } from './UploadPanel';

// Mock the dependencies
vi.mock('../api/client', () => ({
  ingestFiles: vi.fn(),
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe('UploadPanel', () => {
  it('renders upload panel with drag and drop zone', () => {
    render(<UploadPanel pid="test-project" onUploadStateChange={() => {}} />);
    
    expect(screen.getByText('Upload Documents')).toBeInTheDocument();
    expect(screen.getByText(/Drag and drop files here/)).toBeInTheDocument();
    expect(screen.getByText(/Accepted formats:/)).toBeInTheDocument();
    expect(screen.getByText(/\.pdf,\.docx,\.xlsx,\.csv,\.png,\.jpg/)).toBeInTheDocument();
  });

  it('shows browse files button', () => {
    render(<UploadPanel pid="test-project" onUploadStateChange={() => {}} />);
    
    expect(screen.getByText('browse files')).toBeInTheDocument();
  });

  it('accepts pid prop', () => {
    render(<UploadPanel pid="test-project-123" onUploadStateChange={() => {}} />);
    
    // Component should render without errors
    expect(screen.getByText('Upload Documents')).toBeInTheDocument();
  });
});
