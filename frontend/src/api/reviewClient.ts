/**
 * API client for EstimAI review endpoints
 * Handles JWT authentication and provides typed methods for review operations
 */

import {
  ReviewResponse,
  PatchRequest,
  PatchResponse,
  JobStatus,
  TakeoffItem,
  EstimateLine,
  EstimatePayload,
  ApiError
} from '../types/review';
import { config } from '../config';
import { getToken, clearToken } from '../state/auth';

/**
 * Get JWT token from localStorage (using centralized auth state)
 */
function getAuthToken(): string | null {
  return getToken();
}

/**
 * Create headers with JWT authentication
 */
function createAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

/**
 * Handle API errors
 */
async function handleApiError(response: Response): Promise<never> {
  let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
  
  // Handle 401 Unauthorized - clear token and throw auth error
  if (response.status === 401) {
    clearToken();
    throw new Error('Authentication required. Please log in again.');
  }
  
  try {
    const errorData: ApiError = await response.json();
    errorMessage = errorData.detail || errorMessage;
  } catch {
    // If we can't parse JSON, use the status text
  }
  
  throw new Error(errorMessage);
}

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${config.api.baseUrl}${endpoint}`;
  const headers = createAuthHeaders();
  const token = getAuthToken();
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      await handleApiError(response);
    }
    
    return response.json();
  } catch (error: any) {
    // Handle network errors (CORS, connection issues, etc.)
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to server. Please check your connection.');
    }
    
    // Re-throw other errors (including 401 auth errors)
    throw error;
  }
}

/**
 * Convert blob to downloadable URL
 */
export function createDownloadUrl(blob: Blob, filename: string): string {
  const url = URL.createObjectURL(blob);
  
  // Clean up the URL after 5 minutes to prevent memory leaks
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 5 * 60 * 1000);
  
  return url;
}

/**
 * Download a blob as a file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = createDownloadUrl(blob, filename);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ============================================================================
// REVIEW API METHODS
// ============================================================================

/**
 * Get takeoff data for review
 */
export async function getTakeoffReview(projectId: string): Promise<ReviewResponse<TakeoffItem>> {
  return apiRequest<ReviewResponse<TakeoffItem>>(`/projects/${projectId}/review/takeoff`);
}

/**
 * Apply patches to takeoff data
 */
export async function patchTakeoffReview(
  projectId: string,
  patches: PatchRequest
): Promise<PatchResponse> {
  return apiRequest<PatchResponse>(`/projects/${projectId}/review/takeoff`, {
    method: 'PATCH',
    body: JSON.stringify(patches),
  });
}

/**
 * Bulk update takeoff items
 */
export async function updateTakeoffItems(
  projectId: string,
  items: Partial<TakeoffItem>[],
  by: string = 'user',
  reason?: string
): Promise<PatchResponse> {
  const patches = items.map(item => ({
    id: item.id!,
    fields: item,
    by,
    reason,
    at: new Date().toISOString(),
  }));
  
  return patchTakeoffReview(projectId, { patches });
}

/**
 * Update single takeoff item
 */
export async function updateTakeoffItem(
  projectId: string,
  itemId: string,
  fields: Partial<TakeoffItem>,
  by: string = 'user',
  reason?: string
): Promise<PatchResponse> {
  return updateTakeoffItems(projectId, [{ id: itemId, ...fields }], by, reason);
}

/**
 * Get estimate data for review
 */
export async function getEstimateReview(projectId: string): Promise<ReviewResponse<EstimateLine>> {
  return apiRequest<ReviewResponse<EstimateLine>>(`/projects/${projectId}/review/estimate`);
}

/**
 * Apply patches to estimate data
 */
export async function patchEstimateReview(
  projectId: string,
  patches: PatchRequest
): Promise<PatchResponse> {
  return apiRequest<PatchResponse>(`/projects/${projectId}/review/estimate`, {
    method: 'PATCH',
    body: JSON.stringify(patches),
  });
}

/**
 * Bulk update estimate lines
 */
export async function updateEstimateLines(
  projectId: string,
  lines: Partial<EstimateLine>[],
  by: string = 'user',
  reason?: string
): Promise<PatchResponse> {
  const patches = lines.map(line => ({
    id: line.id!,
    fields: line,
    by,
    reason,
    at: new Date().toISOString(),
  }));
  
  return patchEstimateReview(projectId, { patches });
}

/**
 * Update estimate markups (overhead, profit, contingency)
 */
export async function updateEstimateMarkups(
  projectId: string,
  markups: {
    overhead_pct?: number;
    profit_pct?: number;
    contingency_pct?: number;
  },
  by: string = 'user',
  reason?: string
): Promise<PatchResponse> {
  // Create a special patch for markup updates
  const patch = {
    id: 'markups',
    fields: markups,
    by,
    reason,
    at: new Date().toISOString(),
  };
  
  return patchEstimateReview(projectId, { patches: [patch] });
}

/**
 * Update single estimate line
 */
export async function updateEstimateLine(
  projectId: string,
  lineId: string,
  fields: Partial<EstimateLine>,
  by: string = 'user',
  reason?: string
): Promise<PatchResponse> {
  return updateEstimateLines(projectId, [{ id: lineId, ...fields }], by, reason);
}

// ============================================================================
// PIPELINE API METHODS
// ============================================================================

/**
 * Start pipeline asynchronously
 */
export async function startPipeline(projectId: string): Promise<{ job_id: string }> {
  return apiRequest<{ job_id: string }>(`/projects/${projectId}/pipeline_async`, {
    method: 'POST',
  });
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/jobs/${jobId}`);
}

/**
 * Poll job status until completion
 */
export async function pollJobStatus(
  jobId: string,
  onUpdate?: (status: JobStatus) => void,
  intervalMs: number = 1000
): Promise<JobStatus> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        
        if (onUpdate) {
          onUpdate(status);
        }
        
        if (status.status === 'succeeded' || status.status === 'failed') {
          resolve(status);
        } else {
          setTimeout(poll, intervalMs);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    poll();
  });
}

// ============================================================================
// BID API METHODS
// ============================================================================

/**
 * Generate bid PDF
 */
export async function generateBid(projectId: string): Promise<{ project_id: string; pdf_path: string }> {
  return apiRequest<{ project_id: string; pdf_path: string }>(`/projects/${projectId}/bid`, {
    method: 'GET',
  });
}

/**
 * Download bid PDF as blob
 */
export async function downloadBidPdf(projectId: string): Promise<Blob> {
  const token = getAuthToken();
  const url = `${config.api.baseUrl}/projects/${projectId}/bid`;
  
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, { headers });
  
  if (!response.ok) {
    await handleApiError(response);
  }
  
  return response.blob();
}

/**
 * Download bid PDF and trigger browser download
 */
export async function downloadBidPdfFile(projectId: string, filename?: string): Promise<void> {
  const blob = await downloadBidPdf(projectId);
  const defaultFilename = `bid-${projectId}-${new Date().toISOString().split('T')[0]}.pdf`;
  downloadBlob(blob, filename || defaultFilename);
}
