// frontend/src/api/client.ts
import type { 
  JobResponse, 
  PipelineAsyncResponse, 
  BidResponse, 
  ArtifactsResponse 
} from '../types/api';

export const API_BASE = 
  (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api';

export const FILE_BASE = 
  (import.meta as any).env?.VITE_FILE_BASE || 'http://localhost:8000';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export async function api<T>(
  path: string,
  options: RequestInit & { method?: HttpMethod } = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
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

// Helper to compute browser-openable file URLs
export function fileUrl(path: string): string {
  return `${FILE_BASE}/${path}`;
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
