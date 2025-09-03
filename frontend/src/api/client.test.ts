import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { fileUrl, pipelineAsync, getJob, listArtifacts, generateBid, login } from './client';

describe('fileUrl', () => {
  it('constructs proper file URLs', () => {
    expect(fileUrl('artifacts/demo/bid/test.pdf')).toBe('http://localhost:8000/artifacts/demo/bid/test.pdf');
  });

  it('handles paths with leading slash', () => {
    expect(fileUrl('/artifacts/demo/bid/test.pdf')).toBe('http://localhost:8000//artifacts/demo/bid/test.pdf');
  });

  it('handles empty paths', () => {
    expect(fileUrl('')).toBe('http://localhost:8000/');
  });
});

// Integration tests - these require the backend to be running
describe('API Integration', () => {
  let testJobId: string;

  it('can start an async pipeline', async () => {
    const response = await pipelineAsync('demo');
    expect(response).toHaveProperty('job_id');
    expect(typeof response.job_id).toBe('string');
    testJobId = response.job_id;
  }, 10000);

  it('can get job status', async () => {
    if (!testJobId) {
      // Use an existing job ID if the previous test didn't run
      testJobId = '4278a32fa74e474990bcd6f8857d151f';
    }
    
    const job = await getJob(testJobId);
    expect(job).toHaveProperty('job_id', testJobId);
    expect(job).toHaveProperty('status');
    expect(['queued', 'running', 'complete', 'failed']).toContain(job.status);
  }, 10000);

  it('can list artifacts', async () => {
    const artifacts = await listArtifacts('demo');
    expect(artifacts).toHaveProperty('project_id', 'demo');
    expect(artifacts).toHaveProperty('artifacts');
    expect(typeof artifacts.artifacts).toBe('object');
  }, 10000);

  it('can generate bid PDF', async () => {
    const response = await generateBid('demo');
    expect(response).toHaveProperty('project_id', 'demo');
    expect(response).toHaveProperty('pdf_path');
    expect(response.pdf_path).toMatch(/^artifacts\/demo\/bid\/.*\.pdf$/);
  }, 10000);

  it('can authenticate with login', async () => {
    const response = await login({
      username: 'demo@example.com',
      password: 'demo123'
    });
    expect(response).toHaveProperty('token');
    expect(response).toHaveProperty('token_type', 'bearer');
    expect(response).toHaveProperty('user');
    expect(response.user).toHaveProperty('email', 'demo@example.com');
    expect(response.user).toHaveProperty('name');
  }, 10000);
});



