/**
 * useRequireAuth hook - redirects to login if user is not authenticated
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getToken } from '../state/auth';

export function useRequireAuth() {
  const navigate = useNavigate();

  useEffect(() => {
    const token = getToken();
    
    if (!token) {
      // Redirect to login page
      navigate('/login', { replace: true });
    }
  }, [navigate]);

  // Return whether user is authenticated
  const isAuthenticated = !!getToken();
  
  return isAuthenticated;
}
