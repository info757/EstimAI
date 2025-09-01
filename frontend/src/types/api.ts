// frontend/src/types/api.ts

export type JobStatus = 'queued' | 'running' | 'complete' | 'failed';

export interface JobResponse {
  job_id: string;
  project_id: string;
  job_type: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  progress: number;
  message: string | null;
  error: string | null;
  artifacts: Record<string, string>;
  meta: {
    summary?: any;
    pdf_path?: string;
    completed_at?: number;
    error_type?: string;
    error_message?: string;
    failed_at?: number;
  };
}

export interface PipelineAsyncResponse {
  job_id: string;
}

export interface BidResponse {
  project_id: string;
  pdf_path: string;
}

export interface ArtifactsResponse {
  project_id: string;
  artifacts: Record<string, string>;
}

export interface ArtifactItem {
  path: string;
  type?: string;
  created_at?: string;
}

// Review types for PR 10
export type ReviewRow = {
  id: string;
  ai: Record<string, any>;
  override?: Record<string, any> | null;
  merged: Record<string, any>;
  confidence?: number | null;
};

export type ReviewResponse = { 
  rows: ReviewRow[];
  project_id: string;
  stage: string;
  total_rows: number;
  overridden_rows: number;
};

export type Patch = {
  id: string;
  fields: Record<string, any>;
  by: string;
  reason?: string | null;
  at: string; // ISO
};

export type PatchResponse = {
  ok: boolean;
  patched: number;
  project_id: string;
  stage: string;
  message: string;
};

export type PipelineSyncResponse = {
  summary: any;
  pdf_path: string;
};
