// frontend/src/components/Toast.tsx
import React from 'react';

export interface ToastOptions {
  link?: string;
  label?: string;
  type?: 'success' | 'error' | 'info';
}

interface ToastProps {
  message: string;
  options?: ToastOptions;
  onDismiss: () => void;
}

export default function Toast({ message, options, onDismiss }: ToastProps) {
  const { link, label, type = 'info' } = options || {};

  const getToastStyles = () => {
    const baseStyles = "fixed top-4 right-4 max-w-sm p-4 rounded-lg shadow-lg border-l-4 z-50";
    
    switch (type) {
      case 'success':
        return `${baseStyles} bg-green-50 border-green-400 text-green-800`;
      case 'error':
        return `${baseStyles} bg-red-50 border-red-400 text-red-800`;
      case 'info':
      default:
        return `${baseStyles} bg-blue-50 border-blue-400 text-blue-800`;
    }
  };

  return (
    <div className={getToastStyles()}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium">{message}</p>
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-sm underline hover:opacity-80"
            >
              {label || 'Open Link'}
            </a>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="ml-4 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Dismiss toast"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
