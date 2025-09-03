import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

// Mock the API client
vi.mock('../api/client', () => ({
  login: vi.fn(),
}));

// Mock the auth state
vi.mock('../state/auth', () => ({
  setToken: vi.fn(),
  setUser: vi.fn(),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
const mockLocation = { state: {}, search: '' };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  };
});

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderLoginPage = () => {
    return render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
  };

  it('renders login form', () => {
    renderLoginPage();
    
    expect(screen.getByText('Sign in to EstimAI')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('shows demo credentials', () => {
    renderLoginPage();
    
    expect(screen.getByText(/Demo credentials:/)).toBeInTheDocument();
    expect(screen.getByText('demo@example.com')).toBeInTheDocument();
    expect(screen.getByText('demo123')).toBeInTheDocument();
  });

  it('handles form submission', async () => {
    const mockLogin = vi.mocked(await import('../api/client')).login;
    const mockSetToken = vi.mocked(await import('../state/auth')).setToken;
    const mockSetUser = vi.mocked(await import('../state/auth')).setUser;
    
    mockLogin.mockResolvedValue({
      token: 'test-token',
      token_type: 'bearer',
      user: { email: 'test@example.com', name: 'Test User' }
    });

    renderLoginPage();
    
    // Fill out form
    fireEvent.change(screen.getByPlaceholderText('Email address'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'password123' }
    });
    
    // Submit form
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'test@example.com',
        password: 'password123'
      });
    });
    
    expect(mockSetToken).toHaveBeenCalledWith('test-token');
    expect(mockSetUser).toHaveBeenCalledWith({
      email: 'test@example.com',
      name: 'Test User'
    });
    expect(mockNavigate).toHaveBeenCalledWith('/projects/demo', { replace: true });
  });

  it('shows error message on login failure', async () => {
    const mockLogin = vi.mocked(await import('../api/client')).login;
    mockLogin.mockRejectedValue(new Error('Invalid credentials'));
    
    renderLoginPage();
    
    // Fill out form
    fireEvent.change(screen.getByPlaceholderText('Email address'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'wrong-password' }
    });
    
    // Submit form
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('disables form during submission', async () => {
    const mockLogin = vi.mocked(await import('../api/client')).login;
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    
    renderLoginPage();
    
    const emailInput = screen.getByPlaceholderText('Email address');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: 'Sign in' });
    
    // Fill out form
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    
    // Submit form
    fireEvent.click(submitButton);
    
    // Check that form is disabled
    expect(emailInput).toBeDisabled();
    expect(passwordInput).toBeDisabled();
    expect(submitButton).toBeDisabled();
    expect(screen.getByText('Signing in...')).toBeInTheDocument();
  });
});
