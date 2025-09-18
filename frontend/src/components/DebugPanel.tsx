import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getToken } from '../state/auth';
import { getTakeoffReview, getEstimateReview } from '../api/reviewClient';
import { getJob } from '../api/client';

interface DebugPanelProps {
  currentJobId?: string | null;
}

interface TokenInfo {
  present: boolean;
  exp?: number;
}

interface ReviewCounts {
  takeoffCount: number;
  estimateCount: number;
}

interface JobStatus {
  id: string;
  status: string;
  progress?: number;
  message?: string;
}

export default function DebugPanel({ currentJobId }: DebugPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [tokenInfo, setTokenInfo] = useState<TokenInfo>({ present: false });
  const [reviewCounts, setReviewCounts] = useState<ReviewCounts>({ takeoffCount: 0, estimateCount: 0 });
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const { pid } = useParams<{ pid: string }>();

  // Get token info
  useEffect(() => {
    const token = getToken();
    if (token) {
      try {
        // Parse JWT to get expiration
        const payload = JSON.parse(atob(token.split('.')[1]));
        setTokenInfo({
          present: true,
          exp: payload.exp ? payload.exp * 1000 : undefined // Convert to milliseconds
        });
      } catch {
        setTokenInfo({ present: true });
      }
    } else {
      setTokenInfo({ present: false });
    }
  }, []);

  // Get review counts
  useEffect(() => {
    if (!pid) return;

    const fetchCounts = async () => {
      try {
        const [takeoffData, estimateData] = await Promise.all([
          getTakeoffReview(pid),
          getEstimateReview(pid)
        ]);
        
        setReviewCounts({
          takeoffCount: takeoffData.rows.length,
          estimateCount: estimateData.rows.length
        });
      } catch (error) {
        console.error('Failed to fetch review counts:', error);
      }
    };

    fetchCounts();
  }, [pid]);

  // Get job status
  useEffect(() => {
    if (!currentJobId) {
      setJobStatus(null);
      return;
    }

    const fetchJobStatus = async () => {
      try {
        const job = await getJob(currentJobId);
        setJobStatus({
          id: currentJobId,
          status: job.status,
          progress: job.progress,
          message: job.message
        });
      } catch (error) {
        console.error('Failed to fetch job status:', error);
        setJobStatus({
          id: currentJobId,
          status: 'error'
        });
      }
    };

    fetchJobStatus();
    
    // Poll job status every 2 seconds if job is running
    const interval = setInterval(() => {
      if (currentJobId) {
        fetchJobStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentJobId]);

  // Don't render in production
  if (import.meta.env.PROD) {
    return null;
  }

  const formatTokenExp = (exp?: number) => {
    if (!exp) return 'N/A';
    const date = new Date(exp);
    const now = new Date();
    const diff = exp - now.getTime();
    
    if (diff < 0) return 'EXPIRED';
    if (diff < 60000) return `${Math.round(diff / 1000)}s`;
    if (diff < 3600000) return `${Math.round(diff / 60000)}m`;
    return `${Math.round(diff / 3600000)}h`;
  };

  const getJobStatusColor = (status: string) => {
    switch (status) {
      case 'queued': return 'text-yellow-600';
      case 'running': return 'text-blue-600';
      case 'complete': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-w-sm">
      {/* Header */}
      <div 
        className="px-3 py-2 bg-gray-100 border-b border-gray-300 rounded-t-lg cursor-pointer flex items-center justify-between"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-xs font-medium text-gray-700">Debug Panel</span>
        <span className="text-xs text-gray-500">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 space-y-2 text-xs">
          {/* Token Info */}
          <div>
            <div className="font-medium text-gray-700 mb-1">Authentication</div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>Token present:</span>
                <span className={tokenInfo.present ? 'text-green-600' : 'text-red-600'}>
                  {tokenInfo.present ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Token exp:</span>
                <span className={tokenInfo.exp && tokenInfo.exp < Date.now() ? 'text-red-600' : 'text-gray-600'}>
                  {formatTokenExp(tokenInfo.exp)}
                </span>
              </div>
            </div>
          </div>

          {/* API Base URL */}
          <div>
            <div className="font-medium text-gray-700 mb-1">API Config</div>
            <div className="text-gray-600 break-all">
              {import.meta.env.VITE_API_BASE || 'Not set'}
            </div>
          </div>

          {/* Current PID */}
          <div>
            <div className="font-medium text-gray-700 mb-1">Project</div>
            <div className="text-gray-600">
              PID: {pid || 'None'}
            </div>
          </div>

          {/* Review Counts */}
          <div>
            <div className="font-medium text-gray-700 mb-1">Review Data</div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>Takeoff rows:</span>
                <span className="text-gray-600">{reviewCounts.takeoffCount}</span>
              </div>
              <div className="flex justify-between">
                <span>Estimate rows:</span>
                <span className="text-gray-600">{reviewCounts.estimateCount}</span>
              </div>
            </div>
          </div>

          {/* Job Status */}
          <div>
            <div className="font-medium text-gray-700 mb-1">Pipeline Job</div>
            {jobStatus ? (
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span className={getJobStatusColor(jobStatus.status)}>
                    {jobStatus.status}
                  </span>
                </div>
                {jobStatus.progress !== undefined && (
                  <div className="flex justify-between">
                    <span>Progress:</span>
                    <span className="text-gray-600">{jobStatus.progress}%</span>
                  </div>
                )}
                {jobStatus.message && (
                  <div className="text-gray-600 text-xs break-words">
                    {jobStatus.message}
                  </div>
                )}
                <div className="text-gray-500 text-xs">
                  ID: {jobStatus.id.substring(0, 8)}...
                </div>
              </div>
            ) : (
              <div className="text-gray-500">No active job</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
