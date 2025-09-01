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
