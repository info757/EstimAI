/**
 * Authentication state management for EstimAI frontend
 */

import type { User } from '../types/auth';

const TOKEN_KEY = 'estimai_auth_token';
const USER_KEY = 'estimai_user';

/**
 * Get the stored authentication token
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store the authentication token
 */
export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Clear the stored authentication token
 */
export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Store user information
 */
export function setUser(user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Get stored user information
 */
export function getUser(): User | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

/**
 * Clear all authentication data
 */
export function logout(): void {
  clearToken();
}

/**
 * Initialize authentication state from localStorage
 */
export function initializeAuth(): { token: string | null; user: User | null } {
  const token = getToken();
  const user = getUser();
  return { token, user };
}
