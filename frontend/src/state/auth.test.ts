import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getToken,
  setToken,
  clearToken,
  setUser,
  getUser,
  isAuthenticated,
  logout,
  initializeAuth
} from './auth';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('Auth State Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
  });

  describe('getToken', () => {
    it('returns token from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('test-token');
      expect(getToken()).toBe('test-token');
      expect(localStorageMock.getItem).toHaveBeenCalledWith('estimai_auth_token');
    });

    it('returns null when no token exists', () => {
      localStorageMock.getItem.mockReturnValue(null);
      expect(getToken()).toBe(null);
    });
  });

  describe('setToken', () => {
    it('stores token in localStorage', () => {
      setToken('new-token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('estimai_auth_token', 'new-token');
    });
  });

  describe('clearToken', () => {
    it('removes token and user from localStorage', () => {
      clearToken();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('estimai_auth_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('estimai_user');
    });
  });

  describe('setUser', () => {
    it('stores user in localStorage', () => {
      const user = { email: 'test@example.com', name: 'Test User' };
      setUser(user);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('estimai_user', JSON.stringify(user));
    });
  });

  describe('getUser', () => {
    it('returns user from localStorage', () => {
      const user = { email: 'test@example.com', name: 'Test User' };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(user));
      expect(getUser()).toEqual(user);
      expect(localStorageMock.getItem).toHaveBeenCalledWith('estimai_user');
    });

    it('returns null when no user exists', () => {
      localStorageMock.getItem.mockReturnValue(null);
      expect(getUser()).toBe(null);
    });

    it('returns null when user data is malformed', () => {
      localStorageMock.getItem.mockReturnValue('invalid-json');
      expect(getUser()).toBe(null);
    });
  });

  describe('isAuthenticated', () => {
    it('returns true when token exists', () => {
      localStorageMock.getItem.mockReturnValue('test-token');
      expect(isAuthenticated()).toBe(true);
    });

    it('returns false when no token exists', () => {
      localStorageMock.getItem.mockReturnValue(null);
      expect(isAuthenticated()).toBe(false);
    });
  });

  describe('logout', () => {
    it('clears all authentication data', () => {
      logout();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('estimai_auth_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('estimai_user');
    });
  });

  describe('initializeAuth', () => {
    it('returns current auth state', () => {
      const token = 'test-token';
      const user = { email: 'test@example.com', name: 'Test User' };
      
      localStorageMock.getItem
        .mockReturnValueOnce(token) // First call for token
        .mockReturnValueOnce(JSON.stringify(user)); // Second call for user
      
      const result = initializeAuth();
      expect(result).toEqual({ token, user });
    });

    it('returns null values when no auth data exists', () => {
      localStorageMock.getItem.mockReturnValue(null);
      const result = initializeAuth();
      expect(result).toEqual({ token: null, user: null });
    });
  });
});
