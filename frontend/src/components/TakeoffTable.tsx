/**
 * TakeoffTable - Inline editable table for reviewing takeoff items
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type { TakeoffItem } from '../types/review';

interface TakeoffTableProps {
  items: Array<{
    id: string;
    ai: TakeoffItem;
    override?: Partial<TakeoffItem>;
    merged: TakeoffItem;
    confidence?: number;
  }>;
  onEdit: (itemId: string, fields: Partial<TakeoffItem>) => Promise<void>;
  loading?: boolean;
  pending?: boolean;
  hasDirtyEdits?: boolean;
}

interface EditingState {
  itemId: string | null;
  field: string | null;
  value: string;
  originalValue: string;
}

interface ToastState {
  type: 'success' | 'error';
  message: string;
  itemId: string;
}

export default function TakeoffTable({ items, onEdit, loading = false, pending = false, hasDirtyEdits = false }: TakeoffTableProps) {
  const navigate = useNavigate();
  const { pid } = useParams<{ pid: string }>();
  
  const [editing, setEditing] = useState<EditingState>({
    itemId: null,
    field: null,
    value: '',
    originalValue: ''
  });
  
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const [optimisticUpdates, setOptimisticUpdates] = useState<Record<string, Partial<TakeoffItem>>>({});
  
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (editing.itemId && editing.field && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing.itemId, editing.field]);

  // Auto-hide toasts after 3 seconds
  useEffect(() => {
    if (toasts.length > 0) {
      const timer = setTimeout(() => {
        setToasts(prev => prev.slice(1));
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toasts]);

  const getConfidenceBadge = (confidence?: number) => {
    if (confidence === undefined || confidence === null) {
      return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">Unknown</span>;
    }
    
    if (confidence < 0.4) {
      return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">Low</span>;
    } else if (confidence < 0.7) {
      return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded">Med</span>;
    } else {
      return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">High</span>;
    }
  };

  const getItemId = (item: TakeoffItem) => {
    // Use first 8 characters of ID as short name
    return item.id.length > 8 ? item.id.substring(0, 8) + '...' : item.id;
  };

  const startEditing = (itemId: string, field: string, currentValue: any) => {
    if (pending) return; // Don't allow editing while pending
    
    setEditing({
      itemId,
      field,
      value: String(currentValue || ''),
      originalValue: String(currentValue || '')
    });
  };

  const cancelEditing = () => {
    setEditing({
      itemId: null,
      field: null,
      value: '',
      originalValue: ''
    });
  };

  const saveEdit = async () => {
    if (!editing.itemId || !editing.field || pending) return;

    const { itemId, field, value } = editing;
    
    // Validate and clamp numeric fields
    if (field === 'quantity') {
      const numValue = parseFloat(value);
      if (isNaN(numValue)) {
        showToast('error', `${field}: Must be a valid number`, itemId);
        return;
      }
      // Clamp to >= 0
      const clampedValue = Math.max(0, numValue);
      if (clampedValue !== numValue) {
        setEditing(prev => ({ ...prev, value: clampedValue.toString() }));
        showToast('error', `${field}: Clamped to minimum value of 0`, itemId);
        return;
      }
    }

    // Apply optimistic update
    setOptimisticUpdates(prev => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: field === 'quantity' ? parseFloat(value) : value
      }
    }));

    try {
      // Prepare the update object
      const updateFields: Partial<TakeoffItem> = {};
      if (field === 'quantity') {
        updateFields.quantity = parseFloat(value);
      } else {
        (updateFields as any)[field] = value;
      }

      // Call the onEdit callback
      await onEdit(itemId, updateFields);
      
      // Clear optimistic update on success
      setOptimisticUpdates(prev => {
        const newUpdates = { ...prev };
        delete newUpdates[itemId];
        return newUpdates;
      });
      
      showToast('success', `${field}: Saved successfully`, itemId);
      cancelEditing();
    } catch (error: any) {
      // Revert optimistic update on error
      setOptimisticUpdates(prev => {
        const newUpdates = { ...prev };
        delete newUpdates[itemId];
        return newUpdates;
      });
      
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to save changes';
      
      showToast('error', `${field}: ${errorMessage}`, itemId);
    }
  };

  const showToast = (type: 'success' | 'error', message: string, itemId: string) => {
    setToasts(prev => [...prev, { type, message, itemId }]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEditing();
    }
  };

  const handleBlur = () => {
    // Small delay to allow Enter key to trigger first
    setTimeout(() => {
      if (editing.itemId && editing.field) {
        saveEdit();
      }
    }, 100);
  };

  const getDisplayValue = (item: TakeoffItem, field: string) => {
    const optimistic = optimisticUpdates[item.id];
    if (optimistic && field in optimistic) {
      return (optimistic as any)[field];
    }
    return (item as any)[field];
  };

  const isEditing = (itemId: string, field: string) => {
    return editing.itemId === itemId && editing.field === field;
  };

  const hasOverrides = (item: any) => {
    return !!item.override;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Takeoff Review</h2>
        </div>
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading takeoff data...</p>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Takeoff Review</h2>
        </div>
        <div className="p-8 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No takeoff items found</h3>
          <p className="text-gray-600 mb-4">Run the pipeline to generate takeoff data from your project files.</p>
          <button
            onClick={() => pid && navigate(`/projects/${pid}`)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Run Pipeline
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Takeoff Review</h2>
            <p className="text-sm text-gray-600 mt-1">
              {items.length} items • Click any field to edit
            </p>
          </div>
          {hasDirtyEdits && (
            <div className="flex items-center text-sm text-orange-600">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Unsaved changes
            </div>
          )}
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-96">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Item
              </th>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Unit
              </th>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantity
              </th>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Assembly ID
              </th>
              <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((row) => {
              const item = row.merged;
              const optimistic = optimisticUpdates[item.id];
              const displayItem = optimistic ? { ...item, ...optimistic } : item;
              
              return (
                <tr key={item.id} className={`${hasOverrides(row) ? 'bg-yellow-50' : ''} ${pending ? 'opacity-50' : ''}`}>
                  {/* Item ID */}
                  <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-mono text-gray-600">
                      {getItemId(item)}
                    </div>
                    {hasOverrides(row) && (
                      <div className="text-xs text-yellow-600">Modified</div>
                    )}
                  </td>

                  {/* Description - Read-only (from assembly_id) */}
                  <td className="px-3 xl:px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {displayItem.assembly_id || '-'}
                    </div>
                  </td>

                  {/* Unit - Read-only */}
                  <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{displayItem.unit}</div>
                  </td>

                  {/* Quantity - Editable */}
                  <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                    {isEditing(item.id, 'qty') ? (
                      <input
                        ref={inputRef}
                        type="number"
                        step="0.01"
                        min="0"
                        value={editing.value}
                        onChange={(e) => setEditing(prev => ({ ...prev, value: e.target.value }))}
                        onKeyDown={handleKeyDown}
                        onBlur={handleBlur}
                        disabled={pending}
                        className="w-20 xl:w-24 px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      />
                    ) : (
                      <div
                        onClick={() => startEditing(item.id, 'qty', displayItem.qty)}
                        className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                      >
                        {displayItem.qty}
                      </div>
                    )}
                  </td>

                  {/* Assembly ID - Editable */}
                  <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                    {isEditing(item.id, 'assembly_id') ? (
                      <input
                        ref={inputRef}
                        type="text"
                        value={editing.value}
                        onChange={(e) => setEditing(prev => ({ ...prev, value: e.target.value }))}
                        onKeyDown={handleKeyDown}
                        onBlur={handleBlur}
                        disabled={pending}
                        className="w-20 xl:w-24 px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      />
                    ) : (
                      <div
                        onClick={() => startEditing(item.id, 'assembly_id', displayItem.assembly_id || '')}
                        className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                      >
                        {displayItem.assembly_id || '-'}
                      </div>
                    )}
                  </td>

                  {/* Confidence - Read-only badge */}
                  <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                    {getConfidenceBadge(row.confidence)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Toast notifications */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((toast, index) => (
          <div
            key={`${toast.itemId}-${index}`}
            className={`px-4 py-2 rounded-lg shadow-lg text-sm font-medium ${
              toast.type === 'success'
                ? 'bg-green-100 text-green-800 border border-green-200'
                : 'bg-red-100 text-red-800 border border-red-200'
            }`}
          >
            <div className="flex items-center">
              {toast.type === 'success' ? (
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              {toast.message}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
