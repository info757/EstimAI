// frontend/src/api/client.ts
import type { 
  JobResponse, 
  PipelineAsyncResponse, 
  BidResponse, 
  ArtifactsResponse,
  ReviewResponse,
  Patch,
  PatchResponse,
  PipelineSyncResponse,
  IngestResponse
} from '../types/api';
import type { LoginRequest, LoginResponse } from '../types/auth';
import { getToken } from '../state/auth';

export const API_BASE = 
  (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api';

export const FILE_BASE = 
  (import.meta as any).env?.VITE_FILE_BASE || 'http://localhost:8000';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export async function api<T>(
  path: string,
  options: RequestInit & { method?: HttpMethod } = {}
): Promise<T> {
  // Get authentication token
  const token = getToken();
  
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      // Add Authorization header if token exists
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    // Handle 401 Unauthorized - clear token and throw error
    if (res.status === 401) {
      import('../state/auth').then(({ clearToken }) => clearToken());
      throw new Error('Authentication required. Please log in again.');
    }
    
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
  }
  const ct = res.headers.get('content-type') || '';
  return (ct.includes('application/json') ? await res.json() : undefined) as T;
}

// convenience helpers
export const get  = <T>(path: string, init?: RequestInit) =>
  api<T>(path, { ...init, method: 'GET' });

export const post = <T>(path: string, body?: unknown, init?: RequestInit) =>
  api<T>(path, {
    ...init,
    method: 'POST',
    body:
      body instanceof FormData
        ? body
        : body !== undefined
          ? JSON.stringify(body)
          : undefined,
  });

export const patch = <T>(path: string, body?: unknown, init?: RequestInit) =>
  api<T>(path, {
    ...init,
    method: 'PATCH',
    body:
      body instanceof FormData
        ? body
        : body !== undefined
          ? JSON.stringify(body)
          : undefined,
  });

// Helper to compute browser-openable file URLs
export function fileUrl(path: string): string {
  return `${FILE_BASE}${path}`;
}

// API Methods for PR 4

export async function pipelineAsync(pid: string): Promise<PipelineAsyncResponse> {
  return await post<PipelineAsyncResponse>(`/projects/${encodeURIComponent(pid)}/pipeline_async`);
}

export async function getJob(id: string): Promise<JobResponse> {
  return await get<JobResponse>(`/jobs/${encodeURIComponent(id)}`);
}

export async function listArtifacts(pid: string): Promise<ArtifactsResponse> {
  return await get<ArtifactsResponse>(`/projects/${encodeURIComponent(pid)}/artifacts`);
}

export async function generateBid(pid: string): Promise<BidResponse> {
  const base = `/projects/${encodeURIComponent(pid)}/bid`;
  try {
    return await post<BidResponse>(base);
  } catch {
    // Fallback to GET if POST not allowed
    return await get<BidResponse>(base);
  }
}

// Review API Methods for PR 10

export async function getTakeoffReview(pid: string): Promise<ReviewResponse> {
  return await get<ReviewResponse>(`/projects/${encodeURIComponent(pid)}/review/takeoff`);
}

export async function patchTakeoffReview(pid: string, patches: Patch[]): Promise<PatchResponse> {
  return await patch<PatchResponse>(`/projects/${encodeURIComponent(pid)}/review/takeoff`, { patches });
}

export async function getEstimateReview(pid: string): Promise<ReviewResponse> {
  return await get<ReviewResponse>(`/projects/${encodeURIComponent(pid)}/review/estimate`);
}

export async function patchEstimateReview(pid: string, patches: Patch[]): Promise<PatchResponse> {
  return await patch<PatchResponse>(`/projects/${encodeURIComponent(pid)}/review/estimate`, { patches });
}

// Pipeline sync method
export async function pipelineSync(pid: string): Promise<PipelineSyncResponse> {
  return await post<PipelineSyncResponse>(`/projects/${encodeURIComponent(pid)}/pipeline_sync`);
}

// Authentication API Methods for PR 15

export async function login(request: LoginRequest): Promise<LoginResponse> {
  const response = await post<LoginResponse>('/auth/login', request);
  
  // Store token and user data on successful login
  if (response.token) {
    import('../state/auth').then(({ setToken, setUser }) => {
      setToken(response.token);
      setUser(response.user);
    });
  }
  
  return response;
}

// File upload API Methods for PR 16

export async function ingestFiles(pid: string, files: File[]): Promise<IngestResponse> {
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  const res = await fetch(`${API_BASE}/projects/${pid}/ingest`, {
    method: "POST",
    headers: { ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
    body: form,
  });
  if (!res.ok) throw new Error(`ingest failed: ${res.status}`);
  return res.json(); // { ok, files_count, index_ids? }
}

// Async ingest API Methods for PR 17
export async function ingestAsync(pid: string, files: File[]): Promise<{ job_id: string }> {
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  return await post<{ job_id: string }>(`/projects/${encodeURIComponent(pid)}/ingest_async`, form);
}

// Demo reset API Method
export async function resetDemo(): Promise<{ ok: boolean }> {
  return await post<{ ok: boolean }>('/demo/reset');
}
