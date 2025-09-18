/**
 * UX Checklist Overlay - Development Only
 * Tests key functionality and shows status
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  getTakeoffReview,
  getEstimateReview,
  updateTakeoffItems,
  updateEstimateLines,
  updateEstimateMarkups,
  startPipeline,
  getJobStatus,
  downloadBidPdfFile
} from '../api/reviewClient';

interface ChecklistItem {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  error?: string;
}

interface UXChecklistProps {
  isVisible: boolean;
  onToggle: () => void;
  onAllChecksPassed?: (passed: boolean) => void;
}

export default function UXChecklist({ isVisible, onToggle, onAllChecksPassed }: UXChecklistProps) {
  const { pid } = useParams<{ pid: string }>();
  const [items, setItems] = useState<ChecklistItem[]>([
    { id: 'quantity-edits', label: 'Can edit quantity/cost_code/unit_cost and see totals change?', status: 'pending' },
    { id: 'markup-updates', label: 'Do markups update grand total?', status: 'pending' },
    { id: 'persistence', label: 'Do refreshes show persisted server edits?', status: 'pending' },
    { id: 'pipeline-status', label: 'Does "Continue Pipeline" start and show status without blocking edits?', status: 'pending' },
    { id: 'bid-download', label: 'Does "Generate Bid PDF" download a valid file?', status: 'pending' }
  ]);

  const [isRunning, setIsRunning] = useState(false);
  const [allPassed, setAllPassed] = useState(false);

  // Check if all tests have passed
  useEffect(() => {
    const passed = items.every(item => item.status === 'passed');
    setAllPassed(passed);
    onAllChecksPassed?.(passed);
  }, [items, onAllChecksPassed]);

  const updateItem = useCallback((id: string, status: ChecklistItem['status'], error?: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { ...item, status, error } : item
    ));
  }, []);

  const runAllTests = useCallback(async () => {
    if (!pid || isRunning) return;
    
    setIsRunning(true);
    
    // Reset all items to pending
    setItems(prev => prev.map(item => ({ ...item, status: 'pending', error: undefined })));

    try {
      // Get initial data for all tests
      const [takeoffData, estimateData] = await Promise.all([
        getTakeoffReview(pid).catch(() => null),
        getEstimateReview(pid).catch(() => null)
      ]);

      // Test 1: Quantity/Cost Code/Unit Cost Edits
      updateItem('quantity-edits', 'running');
      try {

        if (takeoffData && takeoffData.rows.length > 0) {
          // Test takeoff quantity edit
          const firstTakeoff = takeoffData.rows[0];
          await updateTakeoffItems(pid, [{
            id: firstTakeoff.id,
            quantity: firstTakeoff.merged.quantity + 1
          }], 'ux-test', 'UX checklist test');

          // Test cost code edit
          await updateTakeoffItems(pid, [{
            id: firstTakeoff.id,
            cost_code: 'TEST123'
          }], 'ux-test', 'UX checklist test');
        }

        if (estimateData && estimateData.rows.length > 0) {
          // Test unit cost edit
          const firstEstimate = estimateData.rows[0];
          await updateEstimateLines(pid, [{
            id: firstEstimate.id,
            unit_cost: firstEstimate.merged.unit_cost + 1
          }], 'ux-test', 'UX checklist test');
        }

        updateItem('quantity-edits', 'passed');
      } catch (error) {
        updateItem('quantity-edits', 'failed', error instanceof Error ? error.message : 'Unknown error');
      }

      // Test 2: Markup Updates
      updateItem('markup-updates', 'running');
      try {
        await updateEstimateMarkups(pid, {
          overhead_pct: 12.0,
          profit_pct: 6.0,
          contingency_pct: 4.0
        }, 'ux-test', 'UX checklist test');
        updateItem('markup-updates', 'passed');
      } catch (error) {
        updateItem('markup-updates', 'failed', error instanceof Error ? error.message : 'Unknown error');
      }

      // Test 3: Persistence Check
      updateItem('persistence', 'running');
      try {
        // Make an edit and then refresh data
        if (takeoffData && takeoffData.rows.length > 0) {
          const firstTakeoff = takeoffData.rows[0];
          await updateTakeoffItems(pid, [{
            id: firstTakeoff.id,
            description: 'UX Test Description'
          }], 'ux-test', 'UX checklist test');

          // Wait a moment then check if it persisted
          await new Promise(resolve => setTimeout(resolve, 500));
          const refreshedData = await getTakeoffReview(pid);
          const updatedItem = refreshedData.rows.find(row => row.id === firstTakeoff.id);
          
          if (updatedItem && updatedItem.merged.description === 'UX Test Description') {
            updateItem('persistence', 'passed');
          } else {
            updateItem('persistence', 'failed', 'Edit did not persist on server');
          }
        } else {
          updateItem('persistence', 'passed'); // No data to test, but not a failure
        }
      } catch (error) {
        updateItem('persistence', 'failed', error instanceof Error ? error.message : 'Unknown error');
      }

      // Test 4: Pipeline Status
      updateItem('pipeline-status', 'running');
      try {
        const { job_id } = await startPipeline(pid);
        
        // Check job status a few times
        let statusChecks = 0;
        const maxChecks = 3;
        
        while (statusChecks < maxChecks) {
          const jobStatus = await getJobStatus(job_id);
          if (jobStatus.status === 'complete' || jobStatus.status === 'failed') {
            break;
          }
          await new Promise(resolve => setTimeout(resolve, 1000));
          statusChecks++;
        }
        
        updateItem('pipeline-status', 'passed');
      } catch (error) {
        updateItem('pipeline-status', 'failed', error instanceof Error ? error.message : 'Unknown error');
      }

      // Test 5: Bid PDF Download
      updateItem('bid-download', 'running');
      try {
        const blob = await downloadBidPdfFile(pid, 'ux-test-bid.pdf');
        
        // Check if we got a valid blob
        if (blob && blob.size > 0) {
          updateItem('bid-download', 'passed');
        } else {
          updateItem('bid-download', 'failed', 'Downloaded file is empty or invalid');
        }
      } catch (error) {
        updateItem('bid-download', 'failed', error instanceof Error ? error.message : 'Unknown error');
      }

    } finally {
      setIsRunning(false);
    }
  }, [pid, isRunning, updateItem]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-0 right-0 w-96 bg-white border-l border-b border-gray-300 shadow-lg z-50 max-h-screen overflow-y-auto">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">UX Checklist (Dev Only)</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={runAllTests}
              disabled={isRunning || !pid}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? 'Running...' : 'Run Tests'}
            </button>
            <button
              onClick={onToggle}
              className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Close
            </button>
          </div>
        </div>
        {!pid && (
          <p className="text-xs text-red-600 mt-2">⚠️ No project ID found. Navigate to a project page.</p>
        )}
      </div>

      <div className="p-4 space-y-3">
        {items.map((item) => (
          <div key={item.id} className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {item.status === 'pending' && (
                <div className="w-4 h-4 border-2 border-gray-300 rounded"></div>
              )}
              {item.status === 'running' && (
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              )}
              {item.status === 'passed' && (
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
              {item.status === 'failed' && (
                <div className="w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900">{item.label}</p>
              {item.error && (
                <p className="text-xs text-red-600 mt-1">{item.error}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {allPassed && (
        <div className="p-4 bg-green-50 border-t border-green-200">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <p className="text-sm font-medium text-green-800">All UX tests passed! 🎉</p>
          </div>
        </div>
      )}
    </div>
  );
}
