/**
 * ReviewClient - API client tests for authentication and error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getTakeoffReview,
  getEstimateReview,
  updateTakeoffItems,
  updateEstimateLines,
  updateEstimateMarkups,
  startPipeline,
  getJobStatus,
  downloadBidPdfFile
} from './reviewClient';

// Mock fetch globally
global.fetch = vi.fn();
const mockFetch = fetch as any;

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

describe('ReviewClient - Authentication and Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue('test-jwt-token');
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Authentication Headers', () => {
    it('includes Authorization header with Bearer token for GET requests', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ project_id: 'test', stage: 'takeoff', rows: [], total_rows: 0, overridden_rows: 0 })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await getTakeoffReview('test-project');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/takeoff'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token'
          })
        })
      );
    });

    it('includes Authorization header with Bearer token for PATCH requests', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ success: true, updated_count: 1 })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await updateTakeoffItems('test-project', [{ id: 'item1', description: 'Test' }], 'user', 'Test update');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/takeoff'),
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token',
            'Content-Type': 'application/json'
          }),
          body: expect.any(String)
        })
      );
    });

    it('includes Authorization header with Bearer token for POST requests', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ job_id: 'test-job-123' })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await startPipeline('test-project');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/pipeline_async'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token'
          })
        })
      );
    });

    it('handles missing token gracefully', async () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      
      const mockResponse = {
        ok: true,
        json: async () => ({ project_id: 'test', stage: 'takeoff', rows: [], total_rows: 0, overridden_rows: 0 })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await getTakeoffReview('test-project');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/takeoff'),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.any(String)
          })
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('throws error for 400 Bad Request responses', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid request data' })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Invalid request data');
    });

    it('throws error for 401 Unauthorized responses', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Authentication required' })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Authentication required');
    });

    it('throws error for 404 Not Found responses', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Project not found' })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('nonexistent-project')).rejects.toThrow('Project not found');
    });

    it('throws error for 500 Internal Server Error responses', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Internal server error' })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Internal server error');
    });

    it('throws generic error when response has no detail', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({})
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Request failed with status 500');
    });

    it('throws error when JSON parsing fails', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Invalid JSON'); }
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Request failed with status 500');
    });

    it('throws error for network failures', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(getTakeoffReview('test-project')).rejects.toThrow('Network error');
    });
  });

  describe('Specific API Endpoints', () => {
    it('handles estimate review requests correctly', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ 
          project_id: 'test', 
          stage: 'estimate', 
          rows: [], 
          total_rows: 0, 
          overridden_rows: 0 
        })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await getEstimateReview('test-project');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/estimate'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token'
          })
        })
      );
    });

    it('handles estimate line updates correctly', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ success: true, updated_count: 1 })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await updateEstimateLines('test-project', [{ id: 'line1', unit_cost: 100.50 }], 'user', 'Test update');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/estimate'),
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token',
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('"unit_cost":100.5')
        })
      );
    });

    it('handles markup updates correctly', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ success: true, updated_count: 1 })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await updateEstimateMarkups('test-project', { overhead_pct: 12.5 }, 'user', 'Test update');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/review/estimate'),
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token',
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('"overhead_pct":12.5')
        })
      );
    });

    it('handles job status requests correctly', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ 
          job_id: 'test-job-123',
          project_id: 'test-project',
          job_type: 'pipeline',
          status: 'running',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:01:00Z',
          progress: 50,
          message: 'Processing...'
        })
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await getJobStatus('test-job-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/jobs/test-job-123'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token'
          })
        })
      );
    });

    it('handles PDF download requests correctly', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
      const mockResponse = {
        ok: true,
        blob: async () => mockBlob
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      // Mock URL.createObjectURL
      const mockCreateObjectURL = vi.fn().mockReturnValue('blob:mock-url');
      global.URL.createObjectURL = mockCreateObjectURL;

      // Mock document.createElement and click
      const mockClick = vi.fn();
      const mockAppendChild = vi.fn();
      const mockRemoveChild = vi.fn();
      global.document.createElement = vi.fn().mockReturnValue({
        href: '',
        download: '',
        click: mockClick
      });
      global.document.body = {
        appendChild: mockAppendChild,
        removeChild: mockRemoveChild
      } as any;

      await downloadBidPdfFile('test-project', 'test-bid.pdf');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/projects/test-project/bid'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token'
          })
        })
      );
    });
  });
});
