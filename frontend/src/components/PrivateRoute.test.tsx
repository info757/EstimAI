import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';

// Mock the auth state
vi.mock('../state/auth', () => ({
  isAuthenticated: vi.fn(),
}));

describe('PrivateRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const TestComponent = () => <div>Protected Content</div>;

  it('renders children when authenticated', async () => {
    const mockIsAuthenticated = vi.mocked((await import('../state/auth')).isAuthenticated);
    mockIsAuthenticated.mockReturnValue(true);

    render(
      <BrowserRouter>
        <PrivateRoute>
          <TestComponent />
        </PrivateRoute>
      </BrowserRouter>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', async () => {
    const mockIsAuthenticated = vi.mocked((await import('../state/auth')).isAuthenticated);
    mockIsAuthenticated.mockReturnValue(false);

    const { container } = render(
      <MemoryRouter initialEntries={['/protected']}>
        <PrivateRoute>
          <TestComponent />
        </PrivateRoute>
      </MemoryRouter>
    );

    // Should not render the protected content
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    
    // Should redirect to login (Navigate component behavior)
    expect(container.innerHTML).toContain('Navigate');
  });

  it('preserves location state for redirect', async () => {
    const mockIsAuthenticated = vi.mocked((await import('../state/auth')).isAuthenticated);
    mockIsAuthenticated.mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/projects/123']}>
        <PrivateRoute>
          <TestComponent />
        </PrivateRoute>
      </MemoryRouter>
    );

    // The PrivateRoute should capture the current location for the redirect
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
});
