import React from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import { isAuthenticated } from '../state/auth';
import config from '../config';

interface DemoAwareRouteProps {
  children: React.ReactNode;
}

export default function DemoAwareRoute({ children }: DemoAwareRouteProps) {
  const location = useLocation();
  const { pid } = useParams<{ pid: string }>();
  
  // Check if this is a demo project and demo mode is enabled
  const isDemoProject = pid === config.demo.projectId;
  const isDemoMode = config.demo.public;
  
  // Allow access if:
  // 1. User is authenticated, OR
  // 2. Demo mode is enabled AND this is the demo project
  if (isAuthenticated() || (isDemoMode && isDemoProject)) {
    return <>{children}</>;
  }
  
  // Redirect to login page with the intended destination
  return <Navigate to="/login" state={{ from: location }} replace />;
}
