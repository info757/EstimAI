/**
 * Example usage of the review API client
 * This file demonstrates how to use the review types and API client
 */

import {
  getTakeoffReview,
  updateTakeoffItem,
  updateTakeoffItems,
  getEstimateReview,
  updateEstimateLine,
  updateEstimateMarkups,
  startPipeline,
  pollJobStatus,
  downloadBidPdfFile,
  createDownloadUrl
} from './reviewClient';

import type { TakeoffItem, EstimateLine, PatchRequest } from '../types/review';

// ============================================================================
// EXAMPLE: Takeoff Review Workflow
// ============================================================================

export async function exampleTakeoffReview(projectId: string) {
  try {
    // 1. Get takeoff data for review
    const takeoffData = await getTakeoffReview(projectId);
    console.log('Takeoff review data:', takeoffData);
    
    // 2. Update a single takeoff item
    await updateTakeoffItem(
      projectId,
      'item-123',
      {
        quantity: 150,
        description: 'Updated concrete quantity',
        confidence: 0.95
      },
      'john.doe@company.com',
      'Field measurement correction'
    );
    
    // 3. Bulk update multiple items
    const updates: Partial<TakeoffItem>[] = [
      { id: 'item-124', quantity: 200, unit: 'sq ft' },
      { id: 'item-125', cost_code: 'C-001', confidence: 0.90 }
    ];
    
    await updateTakeoffItems(projectId, updates, 'john.doe@company.com', 'Bulk corrections');
    
    console.log('Takeoff review completed successfully');
  } catch (error) {
    console.error('Takeoff review failed:', error);
  }
}

// ============================================================================
// EXAMPLE: Estimate Review Workflow
// ============================================================================

export async function exampleEstimateReview(projectId: string) {
  try {
    // 1. Get estimate data for review
    const estimateData = await getEstimateReview(projectId);
    console.log('Estimate review data:', estimateData);
    
    // 2. Update unit costs for specific lines
    await updateEstimateLine(
      projectId,
      'line-456',
      {
        unit_cost: 85.50,
        extended_cost: 12825.00 // quantity * unit_cost
      },
      'jane.smith@company.com',
      'Updated market pricing'
    );
    
    // 3. Update markup percentages
    await updateEstimateMarkups(
      projectId,
      {
        overhead_pct: 12.0,
        profit_pct: 8.5,
        contingency_pct: 5.0
      },
      'jane.smith@company.com',
      'Adjusted for project risk'
    );
    
    console.log('Estimate review completed successfully');
  } catch (error) {
    console.error('Estimate review failed:', error);
  }
}

// ============================================================================
// EXAMPLE: Full Pipeline Workflow
// ============================================================================

export async function exampleFullPipeline(projectId: string) {
  try {
    // 1. Start pipeline asynchronously
    const { job_id } = await startPipeline(projectId);
    console.log('Pipeline started with job ID:', job_id);
    
    // 2. Poll job status with progress updates
    const finalStatus = await pollJobStatus(
      job_id,
      (status) => {
        console.log(`Job ${job_id} status: ${status.status} (${status.progress}%)`);
        if (status.message) {
          console.log('Message:', status.message);
        }
      },
      2000 // Poll every 2 seconds
    );
    
    if (finalStatus.status === 'succeeded') {
      console.log('Pipeline completed successfully!');
      console.log('Summary:', finalStatus.meta.summary);
      console.log('PDF path:', finalStatus.meta.pdf_path);
      
      // 3. Download the generated bid PDF
      await downloadBidPdfFile(projectId, `bid-${projectId}-${new Date().toISOString().split('T')[0]}.pdf`);
      console.log('Bid PDF downloaded');
    } else {
      console.error('Pipeline failed:', finalStatus.error);
    }
  } catch (error) {
    console.error('Pipeline workflow failed:', error);
  }
}

// ============================================================================
// EXAMPLE: Manual Patch Request
// ============================================================================

export async function exampleManualPatch(projectId: string) {
  try {
    // Create a manual patch request (for advanced use cases)
    const patchRequest: PatchRequest = {
      patches: [
        {
          id: 'item-789',
          fields: {
            quantity: 300,
            unit: 'linear feet',
            description: 'Updated fence length',
            confidence: 0.98
          },
          by: 'field.engineer@company.com',
          reason: 'Site survey correction',
          at: new Date().toISOString()
        }
      ]
    };
    
    // Apply the patch using the low-level API
    const response = await updateTakeoffItems(projectId, patchRequest.patches.map(p => ({
      id: p.id,
      ...p.fields
    })), patchRequest.patches[0].by, patchRequest.patches[0].reason);
    
    console.log('Manual patch applied:', response);
  } catch (error) {
    console.error('Manual patch failed:', error);
  }
}

// ============================================================================
// EXAMPLE: Blob Handling
// ============================================================================

export async function exampleBlobHandling(projectId: string) {
  try {
    // Download PDF as blob
    const response = await fetch(`/api/projects/${projectId}/bid`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const blob = await response.blob();
    
    // Create download URL
    const downloadUrl = createDownloadUrl(blob, `bid-${projectId}.pdf`);
    
    // Open in new tab
    window.open(downloadUrl, '_blank');
    
    console.log('PDF opened in new tab');
  } catch (error) {
    console.error('Blob handling failed:', error);
  }
}
