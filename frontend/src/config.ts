/**
 * Frontend configuration for EstimAI
 * Reads environment variables and provides defaults
 */

export const config = {
  // Demo mode configuration
  demo: {
    public: import.meta.env.VITE_DEMO_PUBLIC === 'true',
    projectId: import.meta.env.VITE_DEMO_PROJECT_ID || 'demo',
  },
  
  // API configuration
  api: {
    baseUrl: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api',
    fileBaseUrl: import.meta.env.VITE_FILE_BASE || 'http://localhost:8000',
  },
} as const;

export default config;
