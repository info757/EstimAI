/**
 * Development Banner - Shows when all UX checks pass
 */

import React from 'react';

interface DevBannerProps {
  allChecksPassed: boolean;
  onToggleChecklist: () => void;
}

export default function DevBanner({ allChecksPassed, onToggleChecklist }: DevBannerProps) {
  // Only show in development
  if (import.meta.env.PROD) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-40">
      <div className={`px-4 py-2 text-center text-sm font-medium ${
        allChecksPassed 
          ? 'bg-green-600 text-white' 
          : 'bg-yellow-600 text-white'
      }`}>
        <div className="flex items-center justify-center gap-2">
          {allChecksPassed ? (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>✅ All UX checks passed!</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>⚠️ UX checks pending</span>
            </>
          )}
          <button
            onClick={onToggleChecklist}
            className="ml-2 px-2 py-1 text-xs bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition-colors"
            title="Toggle UX Checklist (Ctrl/Cmd + Shift + U)"
          >
            Toggle Checklist
          </button>
        </div>
      </div>
    </div>
  );
}
