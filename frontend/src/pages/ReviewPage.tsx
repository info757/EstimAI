/**
 * ReviewPage - Human-in-the-loop review interface for takeoff and estimate data
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { useRequireAuth } from '../hooks/useRequireAuth';
import {
  getTakeoffReview,
  getEstimateReview,
  updateTakeoffItems,
  updateEstimateLines,
  updateEstimateMarkups,
  startPipeline,
  pollJobStatus,
  downloadBidPdfFile
} from '../api/reviewClient';
import { listArtifacts } from '../api/client';
import TakeoffTable from '../components/TakeoffTable';
import EstimateTable from '../components/EstimateTable';
import UXChecklist from '../components/UXChecklist';
import DevBanner from '../components/DevBanner';
import DebugPanel from '../components/DebugPanel';
import Toast from '../components/Toast';
import type {
  ReviewResponse,
  TakeoffItem,
  EstimateLine,
  EstimatePayload,
  JobStatus
} from '../types/review';

interface ReviewState {
  takeoff: ReviewResponse<TakeoffItem> | null;
  estimate: ReviewResponse<EstimateLine> | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  recalculating: boolean;
  pipelineRunning: boolean;
  currentJobId: string | null;
  jobStatus: JobStatus | null;
  pollingError: string | null;
  hasIngestedFiles: boolean | null; // null = unknown, true = files present, false = no files
  markups: {
    overhead_pct: number;
    profit_pct: number;
    contingency_pct: number;
  };
}

// Map to store takeoff items by ID for quantity resolution
type TakeoffMap = Map<string, TakeoffItem>;

export default function ReviewPage() {
  const { pid } = useParams<{ pid: string }>();
  const [searchParams] = useSearchParams();
  const isAuthenticated = useRequireAuth();
  
  // Refs for auto-focusing sections
  const takeoffSectionRef = useRef<HTMLDivElement>(null);
  const estimateSectionRef = useRef<HTMLDivElement>(null);
  
  
  const [state, setState] = useState<ReviewState>({
    takeoff: null,
    estimate: null,
    loading: true,
    error: null,
    saving: false,
    recalculating: false,
    pipelineRunning: false,
    currentJobId: null,
    jobStatus: null,
    pollingError: null,
    hasIngestedFiles: null,
    markups: {
      overhead_pct: 10.0,
      profit_pct: 5.0,
      contingency_pct: 3.0
    }
  });

  const [takeoffMap, setTakeoffMap] = useState<TakeoffMap>(new Map());
  const [optimisticUpdates, setOptimisticUpdates] = useState<Record<string, any>>({});
  
  // Toast state
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  
  // UX Checklist state (dev only)
  const [showUXChecklist, setShowUXChecklist] = useState(false);
  const [allUXChecksPassed, setAllUXChecksPassed] = useState(false);

  // Toast functions
  const showToast = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    setToast({ type, message });
  }, []);

  const hideToast = useCallback(() => {
    setToast(null);
  }, []);

  // Keyboard shortcut for UX checklist (dev only)
  useEffect(() => {
    if (import.meta.env.PROD) return;
    
    const handleKeyPress = (event: KeyboardEvent) => {
      // Ctrl/Cmd + Shift + U to toggle UX checklist
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'U') {
        event.preventDefault();
        setShowUXChecklist(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  // Fetch data on mount
  useEffect(() => {
    if (!pid || !isAuthenticated) return;
    
    fetchReviewData();
  }, [pid, isAuthenticated]);

  // Auto-focus section based on URL parameter
  useEffect(() => {
    const focusParam = searchParams.get('focus');
    if (!focusParam || state.loading) return;

    // Small delay to ensure DOM is ready
    const timer = setTimeout(() => {
      if (focusParam === 'takeoff' && takeoffSectionRef.current) {
        takeoffSectionRef.current.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
        // Add a subtle highlight effect
        takeoffSectionRef.current.style.transition = 'box-shadow 0.3s ease';
        takeoffSectionRef.current.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.3)';
        setTimeout(() => {
          if (takeoffSectionRef.current) {
            takeoffSectionRef.current.style.boxShadow = '';
          }
        }, 2000);
      } else if (focusParam === 'estimate' && estimateSectionRef.current) {
        estimateSectionRef.current.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
        // Add a subtle highlight effect
        estimateSectionRef.current.style.transition = 'box-shadow 0.3s ease';
        estimateSectionRef.current.style.boxShadow = '0 0 0 3px rgba(147, 51, 234, 0.3)';
        setTimeout(() => {
          if (estimateSectionRef.current) {
            estimateSectionRef.current.style.boxShadow = '';
          }
        }, 2000);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [searchParams, state.loading]);

  const fetchReviewData = async () => {
    if (!pid) return;
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Fetch takeoff data with logging
      let takeoffData = null;
      try {
        takeoffData = await getTakeoffReview(pid);
        console.log(`review: GET /review/takeoff for pid=${pid} - status=200, response_length=${JSON.stringify(takeoffData).length}, rows=${takeoffData.rows.length}`);
      } catch (error: any) {
        console.log(`review: GET /review/takeoff for pid=${pid} - status=${error?.response?.status || 'unknown'}, error=${error?.message}`);
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          showToast('error', 'Authentication required. Please log in again.');
        }
        // Don't throw here, continue with null data
      }

      // Fetch estimate data with logging
      let estimateData = null;
      try {
        estimateData = await getEstimateReview(pid);
        console.log(`review: GET /review/estimate for pid=${pid} - status=200, response_length=${JSON.stringify(estimateData).length}, rows=${estimateData.rows.length}`);
      } catch (error: any) {
        console.log(`review: GET /review/estimate for pid=${pid} - status=${error?.response?.status || 'unknown'}, error=${error?.message}`);
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          showToast('error', 'Authentication required. Please log in again.');
        }
        // Don't throw here, continue with null data
      }

      // Check for empty data and show appropriate toast
      if (takeoffData && estimateData && takeoffData.rows.length === 0 && estimateData.rows.length === 0) {
        console.log(`review: Both takeoff and estimate are empty for pid=${pid} - pipeline likely not run`);
        showToast('info', 'No review data found. Run the pipeline to generate takeoff and estimate data.');
      }

      // Fetch artifacts data (gracefully handle failure)
      const artifactsData = await listArtifacts(pid).catch(() => ({ artifacts: {} }));
      
      // Check if files have been ingested (look for docs directory or any artifacts)
      // artifactsData.artifacts is an object, not an array, so we check Object.values()
      const hasIngestedFiles = Object.values(artifactsData.artifacts).some(artifactPath => 
        artifactPath.includes('/docs/') || 
        artifactPath.includes('sheet_index.json') || 
        artifactPath.includes('spec_index.json')
      );
      
      // Build takeoff map for quantity resolution
      const newTakeoffMap = new Map<string, TakeoffItem>();
      if (takeoffData && takeoffData.rows) {
        takeoffData.rows.forEach(row => {
          newTakeoffMap.set(row.id, row.merged);
        });
      }
      setTakeoffMap(newTakeoffMap);
      
      setState(prev => ({
        ...prev,
        takeoff: takeoffData,
        estimate: estimateData,
        hasIngestedFiles,
        loading: false
      }));
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to load review data';
      
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage
      }));
    }
  };

  const handleTakeoffUpdate = async (itemId: string, fields: Partial<TakeoffItem>) => {
    if (!pid) return;
    
    setState(prev => ({ ...prev, saving: true }));
    
    try {
      // Call PATCH /review/takeoff with single item update
      await updateTakeoffItems(pid, [{ id: itemId, ...fields }], 'user', 'Review update');
      
      // Refresh takeoff data and update map
      const updatedTakeoff = await getTakeoffReview(pid);
      const newTakeoffMap = new Map<string, TakeoffItem>();
      updatedTakeoff.rows.forEach(row => {
        newTakeoffMap.set(row.id, row.merged);
      });
      setTakeoffMap(newTakeoffMap);
      
      setState(prev => ({ ...prev, takeoff: updatedTakeoff, saving: false }));
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to update takeoff item';
      
      setState(prev => ({
        ...prev,
        saving: false,
        error: errorMessage
      }));
    }
  };

  const handleEstimateLineUpdate = async (lineId: string, fields: { unit_cost?: number }) => {
    if (!pid) return;
    
    setState(prev => ({ ...prev, saving: true }));
    
    try {
      // Call PATCH /review/estimate with single line update
      await updateEstimateLines(pid, [{ id: lineId, ...fields }], 'user', 'Review update');
      
      // Refresh estimate data
      const updatedEstimate = await getEstimateReview(pid);
      setState(prev => ({ ...prev, estimate: updatedEstimate, saving: false }));
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to update estimate line';
      
      setState(prev => ({
        ...prev,
        saving: false,
        error: errorMessage
      }));
    }
  };

  const handleMarkupUpdate = async (markups: {
    overhead_pct?: number;
    profit_pct?: number;
    contingency_pct?: number;
  }) => {
    if (!pid) return;
    
    setState(prev => ({ ...prev, saving: true }));
    
    try {
      // Call PATCH /review/estimate with markup update
      await updateEstimateMarkups(pid, markups, 'user', 'Markup adjustment');
      
      // Update local markups state
      setState(prev => ({
        ...prev,
        markups: { ...prev.markups, ...markups },
        saving: false
      }));
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to update markups';
      
      setState(prev => ({
        ...prev,
        saving: false,
        error: errorMessage
      }));
    }
  };

  // Recalculate client-side totals
  const handleRecalculate = useCallback(() => {
    setState(prev => ({ ...prev, recalculating: true }));
    
    // Simulate recalculation delay
    setTimeout(() => {
      setState(prev => ({ ...prev, recalculating: false }));
    }, 500);
  }, []);

  // Continue pipeline
  const handleContinuePipeline = useCallback(async () => {
    if (!pid) return;
    
    setState(prev => ({ ...prev, pipelineRunning: true, currentJobId: null, jobStatus: null, pollingError: null }));
    
    try {
      // Start pipeline
      const { job_id } = await startPipeline(pid);
      setState(prev => ({ ...prev, currentJobId: job_id }));
      
      // Poll job status
      const finalStatus = await pollJobStatus(
        job_id,
        (status) => {
          setState(prev => ({ ...prev, jobStatus: status }));
        },
        2000 // Poll every 2 seconds
      );
      
      setState(prev => ({ 
        ...prev, 
        pipelineRunning: false, 
        jobStatus: finalStatus 
      }));
      
      if (finalStatus.status === 'succeeded') {
        // Refresh data after successful pipeline
        await fetchReviewData();
      }
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Pipeline failed';
      
      setState(prev => ({
        ...prev,
        pipelineRunning: false,
        pollingError: errorMessage
      }));
    }
  }, [pid, fetchReviewData]);

  // Generate bid PDF
  const handleGenerateBid = useCallback(async () => {
    if (!pid) return;
    
    try {
      await downloadBidPdfFile(pid, `bid-${pid}.pdf`);
    } catch (error: any) {
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to generate bid PDF';
      
      setState(prev => ({
        ...prev,
        error: errorMessage
      }));
    }
  }, [pid]);

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  if (state.loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading review data...</p>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="text-red-600 mr-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-red-800 font-medium">Error loading review data</h3>
            <p className="text-red-600 mt-1">{state.error}</p>
            <button
              onClick={fetchReviewData}
              disabled={state.loading}
              className="mt-3 text-sm bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {state.loading ? (
                <>
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-red-800 mr-2"></div>
                  Retrying...
                </>
              ) : (
                'Retry'
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Development Banner */}
      <DevBanner 
        allChecksPassed={allUXChecksPassed}
        onToggleChecklist={() => setShowUXChecklist(!showUXChecklist)}
      />
      
      {/* UX Checklist Overlay */}
      <UXChecklist 
        isVisible={showUXChecklist}
        onToggle={() => setShowUXChecklist(!showUXChecklist)}
        onAllChecksPassed={setAllUXChecksPassed}
      />
      
      <div className="max-w-7xl mx-auto p-6" style={{ marginTop: import.meta.env.PROD ? 0 : '40px' }}>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Project Review</h1>
            <p className="text-gray-600 mt-1">Project ID: {pid}</p>
          </div>
          
          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleRecalculate}
              disabled={state.recalculating}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {state.recalculating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Recalculating...
                </>
              ) : (
                'Recalculate'
              )}
            </button>
            
            <button
              onClick={handleContinuePipeline}
              disabled={state.pipelineRunning}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {state.pipelineRunning ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Running...
                </>
              ) : (
                'Continue Pipeline'
              )}
            </button>
            
            <button
              onClick={handleGenerateBid}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Generate Bid PDF
            </button>
          </div>
        </div>
        
        {/* Status Indicators */}
        <div className="mt-3 space-y-2">
          {state.saving && (
            <div className="text-sm text-blue-600 flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              Saving changes...
            </div>
          )}
          
          {state.jobStatus && state.jobStatus.status === 'succeeded' && (
            <div className="text-sm text-green-600 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Pipeline completed successfully!
            </div>
          )}
        </div>
      </div>

      {/* State-based Empty State Banners */}
      {!state.loading && !state.error && state.takeoff && state.estimate && (
        <>
          {/* State 1: No files ingested */}
          {state.hasIngestedFiles === false && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="text-blue-600 mr-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-blue-800 font-medium">No files ingested</h3>
                    <p className="text-blue-600 mt-1">Upload PDF files to get started with your project.</p>
                  </div>
                </div>
                <Link
                  to="/upload"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Go to Upload
                </Link>
              </div>
            </div>
          )}

          {/* State 2: Files present but no review data */}
          {state.hasIngestedFiles === true && 
           state.takeoff.rows.length === 0 && state.estimate.rows.length === 0 && 
           !state.pipelineRunning && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="text-yellow-600 mr-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-yellow-800 font-medium">
                      {(() => {
                        const focusParam = searchParams.get('focus');
                        if (focusParam === 'takeoff') return 'No takeoff data found';
                        if (focusParam === 'estimate') return 'No estimate data found';
                        return 'No review data found';
                      })()}
                    </h3>
                    <p className="text-yellow-600 mt-1">
                      {(() => {
                        const focusParam = searchParams.get('focus');
                        if (focusParam === 'takeoff') return 'Run pipeline to generate takeoff quantities from uploaded files.';
                        if (focusParam === 'estimate') return 'Run pipeline to generate estimate pricing from uploaded files.';
                        return 'Run pipeline to generate takeoff & estimate data from uploaded files.';
                      })()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleContinuePipeline}
                  disabled={state.pipelineRunning}
                  className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Run Pipeline
                </button>
              </div>
            </div>
          )}

          {/* State 3: Pipeline running */}
          {state.pipelineRunning && state.jobStatus && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="text-blue-600 mr-3">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  </div>
                  <div>
                    <h3 className="text-blue-800 font-medium">Pipeline running</h3>
                    <p className="text-blue-600 mt-1">
                      {state.jobStatus.progress !== undefined 
                        ? `${state.jobStatus.progress}% complete`
                        : 'Processing your files...'
                      }
                      {state.jobStatus.message && ` - ${state.jobStatus.message}`}
                    </p>
                  </div>
                </div>
                <div className="text-sm text-blue-600">
                  You can continue browsing while this runs
                </div>
              </div>
            </div>
          )}

          {/* State 4: Pipeline failed */}
          {state.jobStatus && state.jobStatus.status === 'failed' && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="text-red-600 mr-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-red-800 font-medium">Pipeline failed</h3>
                    <p className="text-red-600 mt-1">
                      {state.jobStatus.error || 'An error occurred during pipeline execution.'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleContinuePipeline}
                    className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors flex items-center"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry Pipeline
                  </button>
                  <a
                    href={`/api/projects/${pid}/artifacts`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors flex items-center"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    View Artifacts
                  </a>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      <div className="grid gap-8">
        {/* Takeoff Review Section */}
        <div ref={takeoffSectionRef}>
          {state.takeoff && (
            <TakeoffTable
              items={state.takeoff.rows}
              onEdit={handleTakeoffUpdate}
              loading={state.loading}
              pending={state.saving}
              hasDirtyEdits={Object.keys(optimisticUpdates).length > 0}
            />
          )}
        </div>

        {/* Estimate Review Section */}
        <div ref={estimateSectionRef}>
          {state.estimate && (
            <EstimateTable
              lines={state.estimate.rows}
              markups={state.markups}
              onEditLine={handleEstimateLineUpdate}
              onEditMarkups={handleMarkupUpdate}
              loading={state.loading}
              pending={state.saving}
              hasDirtyEdits={Object.keys(optimisticUpdates).length > 0}
            />
          )}
        </div>

        {/* Artifacts Debug Panel */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Debug</h3>
          <div className="text-xs text-gray-600">
            <a
              href={`/api/projects/${pid}/artifacts`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              View Artifacts Directory
            </a>
          </div>
        </div>
      </div>
    </div>
    
    {/* Debug Panel */}
    <DebugPanel currentJobId={state.currentJobId} />
    
    {/* Toast */}
    {toast && (
      <Toast
        type={toast.type}
        message={toast.message}
        onClose={hideToast}
      />
    )}
    </>
  );
}


