/**
 * TypeScript types for EstimAI review system
 */

// Base types for takeoff items
export interface TakeoffItem {
  id: string;
  description: string;
  unit: string;
  quantity: number;
  cost_code?: string;
  confidence?: number;
}

// Base types for estimate lines
export interface EstimateLine {
  id: string;
  description: string;
  unit: string;
  quantity: number;
  unit_cost: number;
  extended_cost: number;
  takeoff_item_id?: string; // Optional link back to takeoff item
  cost_code?: string;
}

// Estimate payload with markup percentages
export interface EstimatePayload {
  lines: EstimateLine[];
  overhead_pct: number;
  profit_pct: number;
  contingency_pct: number;
  subtotal: number;
  overhead_amount: number;
  profit_amount: number;
  contingency_amount: number;
  total_bid: number;
}

// Review response structure (matches backend)
export interface ReviewResponse<T = any> {
  project_id: string;
  stage: 'takeoff' | 'estimate';
  rows: ReviewRow<T>[];
  total_rows: number;
  overridden_rows: number;
}

// Individual review row with AI, override, and merged data
export interface ReviewRow<T = any> {
  id: string;
  ai: T; // Original AI-generated data
  override?: Partial<T>; // Override fields (if any)
  merged: T; // AI ⊕ override result
  confidence?: number; // AI confidence score
}

// Patch request for bulk updates
export interface PatchRequest {
  patches: Patch[];
}

// Individual patch
export interface Patch {
  id: string;
  fields: Record<string, any>;
  by: string;
  reason?: string;
  at: string; // ISO timestamp
}

// Patch response
export interface PatchResponse {
  ok: boolean;
  patched: number;
  project_id: string;
  stage: 'takeoff' | 'estimate';
  message: string;
}

// Job status for polling
export interface JobStatus {
  job_id: string;
  project_id: string;
  job_type: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  created_at: string;
  updated_at: string;
  progress: number;
  message?: string;
  error?: string;
  artifacts: Record<string, any>;
  meta: {
    summary?: string;
    pdf_path?: string;
  };
}

// API error response
export interface ApiError {
  detail: string;
  status_code?: number;
}
