/**
 * EstimateTable - Inline editable table for reviewing estimate lines with markups
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type { EstimateLine } from '../types/review';

interface EstimateTableProps {
  lines: Array<{
    id: string;
    ai: EstimateLine;
    override?: Partial<EstimateLine>;
    merged: EstimateLine;
    confidence?: number;
  }>;
  markups: {
    overhead_pct: number;
    profit_pct: number;
    contingency_pct: number;
  };
  onEditLine: (lineId: string, fields: { unit_cost?: number }) => Promise<void>;
  onEditMarkups: (markups: {
    overhead_pct?: number;
    profit_pct?: number;
    contingency_pct?: number;
  }) => Promise<void>;
  loading?: boolean;
  pending?: boolean;
  hasDirtyEdits?: boolean;
}

interface EditingState {
  lineId: string | null;
  field: string | null;
  value: string;
  originalValue: string;
}

interface MarkupEditingState {
  field: string | null;
  value: string;
  originalValue: string;
}

interface ToastState {
  type: 'success' | 'error';
  message: string;
  itemId?: string;
}

export default function EstimateTable({ 
  lines, 
  markups, 
  onEditLine, 
  onEditMarkups, 
  loading = false,
  pending = false,
  hasDirtyEdits = false
}: EstimateTableProps) {
  const navigate = useNavigate();
  const { pid } = useParams<{ pid: string }>();
  
  const [editing, setEditing] = useState<EditingState>({
    lineId: null,
    field: null,
    value: '',
    originalValue: ''
  });
  
  const [markupEditing, setMarkupEditing] = useState<MarkupEditingState>({
    field: null,
    value: '',
    originalValue: ''
  });
  
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const [optimisticUpdates, setOptimisticUpdates] = useState<Record<string, Partial<EstimateLine>>>({});
  const [optimisticMarkups, setOptimisticMarkups] = useState<Partial<typeof markups>>({});
  
  const inputRef = useRef<HTMLInputElement>(null);
  const markupInputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (editing.lineId && editing.field && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing.lineId, editing.field]);

  useEffect(() => {
    if (markupEditing.field && markupInputRef.current) {
      markupInputRef.current.focus();
      markupInputRef.current.select();
    }
  }, [markupEditing.field]);

  // Auto-hide toasts after 3 seconds
  useEffect(() => {
    if (toasts.length > 0) {
      const timer = setTimeout(() => {
        setToasts(prev => prev.slice(1));
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toasts]);

  // Calculate totals
  const calculateTotals = () => {
    const currentMarkups = { ...markups, ...optimisticMarkups };
    
    let subtotal = 0;
    lines.forEach(line => {
      const optimistic = optimisticUpdates[line.id];
      const displayLine = optimistic ? { ...line.merged, ...optimistic } : line.merged;
      
      // Use quantity from takeoff item if available, fallback to 1
      const quantity = displayLine.takeoff_item_id ? displayLine.qty : (displayLine.qty || 1);
      const unitCost = displayLine.unit_cost || 0;
      const extendedCost = quantity * unitCost;
      
      subtotal += extendedCost;
    });

    const overheadAmount = subtotal * (currentMarkups.overhead_pct / 100);
    const profitAmount = subtotal * (currentMarkups.profit_pct / 100);
    const contingencyAmount = subtotal * (currentMarkups.contingency_pct / 100);
    
    const totalMarkup = currentMarkups.overhead_pct + currentMarkups.profit_pct + currentMarkups.contingency_pct;
    const grandTotal = subtotal * (1 + totalMarkup / 100);

    return {
      subtotal,
      overheadAmount,
      profitAmount,
      contingencyAmount,
      totalMarkup,
      grandTotal
    };
  };

  const totals = calculateTotals();

  const startEditing = (lineId: string, field: string, currentValue: any) => {
    if (pending) return; // Don't allow editing while pending
    
    setEditing({
      lineId,
      field,
      value: String(currentValue || ''),
      originalValue: String(currentValue || '')
    });
  };

  const startMarkupEditing = (field: string, currentValue: any) => {
    if (pending) return; // Don't allow editing while pending
    
    setMarkupEditing({
      field,
      value: String(currentValue || ''),
      originalValue: String(currentValue || '')
    });
  };

  const cancelEditing = () => {
    setEditing({
      lineId: null,
      field: null,
      value: '',
      originalValue: ''
    });
  };

  const cancelMarkupEditing = () => {
    setMarkupEditing({
      field: null,
      value: '',
      originalValue: ''
    });
  };

  const saveEdit = async () => {
    if (!editing.lineId || !editing.field || pending) return;

    const { lineId, field, value } = editing;
    
    // Validate and clamp numeric fields
    if (field === 'unit_cost') {
      const numValue = parseFloat(value);
      if (isNaN(numValue)) {
        showToast('error', `${field}: Must be a valid number`, lineId);
        return;
      }
      // Clamp to >= 0
      const clampedValue = Math.max(0, numValue);
      if (clampedValue !== numValue) {
        setEditing(prev => ({ ...prev, value: clampedValue.toString() }));
        showToast('error', `${field}: Clamped to minimum value of 0`, lineId);
        return;
      }
    }

    // Apply optimistic update
    setOptimisticUpdates(prev => ({
      ...prev,
      [lineId]: {
        ...prev[lineId],
        [field]: field === 'unit_cost' ? parseFloat(value) : value
      }
    }));

    try {
      const updateFields: { unit_cost?: number } = {};
      if (field === 'unit_cost') {
        updateFields.unit_cost = parseFloat(value);
      }

      await onEditLine(lineId, updateFields);
      
      // Clear optimistic update on success
      setOptimisticUpdates(prev => {
        const newUpdates = { ...prev };
        delete newUpdates[lineId];
        return newUpdates;
      });
      
      showToast('success', `${field}: Updated successfully`, lineId);
      cancelEditing();
    } catch (error: any) {
      // Revert optimistic update on error
      setOptimisticUpdates(prev => {
        const newUpdates = { ...prev };
        delete newUpdates[lineId];
        return newUpdates;
      });
      
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to update line';
      
      showToast('error', `${field}: ${errorMessage}`, lineId);
    }
  };

  const saveMarkupEdit = async () => {
    if (!markupEditing.field || pending) return;

    const { field, value } = markupEditing;
    
    // Validate and clamp percentage fields (0-30% by default)
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      showToast('error', `${field}: Must be a valid number`);
      return;
    }
    // Clamp to 0-30% range
    const clampedValue = Math.max(0, Math.min(30, numValue));
    if (clampedValue !== numValue) {
      setMarkupEditing(prev => ({ ...prev, value: clampedValue.toString() }));
      showToast('error', `${field}: Clamped to 0-30% range`);
      return;
    }

    // Apply optimistic update
    setOptimisticMarkups(prev => ({
      ...prev,
      [field]: numValue
    }));

    try {
      const updateFields: any = {};
      updateFields[field] = numValue;

      await onEditMarkups(updateFields);
      
      // Clear optimistic update on success
      setOptimisticMarkups({});
      
      showToast('success', `${field}: Updated successfully`);
      cancelMarkupEditing();
    } catch (error: any) {
      // Revert optimistic update on error
      setOptimisticMarkups({});
      
      // Extract error message from backend if available
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to update markups';
      
      showToast('error', `${field}: ${errorMessage}`);
    }
  };

  const showToast = (type: 'success' | 'error', message: string, itemId?: string) => {
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

  const handleMarkupKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveMarkupEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelMarkupEditing();
    }
  };

  const handleBlur = () => {
    setTimeout(() => {
      if (editing.lineId && editing.field) {
        saveEdit();
      }
    }, 100);
  };

  const handleMarkupBlur = () => {
    setTimeout(() => {
      if (markupEditing.field) {
        saveMarkupEdit();
      }
    }, 100);
  };

  const getDisplayValue = (line: EstimateLine, field: string) => {
    const optimistic = optimisticUpdates[line.id];
    if (optimistic && field in optimistic) {
      return (optimistic as any)[field];
    }
    return (line as any)[field];
  };

  const getDisplayMarkup = (field: string) => {
    if (optimisticMarkups[field as keyof typeof markups] !== undefined) {
      return optimisticMarkups[field as keyof typeof markups]!;
    }
    return markups[field as keyof typeof markups];
  };

  const isEditing = (lineId: string, field: string) => {
    return editing.lineId === lineId && editing.field === field;
  };

  const isMarkupEditing = (field: string) => {
    return markupEditing.field === field;
  };

  const hasOverrides = (line: any) => {
    return !!line.override;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Estimate Review</h2>
        </div>
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading estimate data...</p>
        </div>
      </div>
    );
  }

  if (lines.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Estimate Review</h2>
        </div>
        <div className="p-8 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No estimate lines found</h3>
          <p className="text-gray-600 mb-4">Run the pipeline to generate estimate data from your takeoff items.</p>
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
            <h2 className="text-lg font-semibold text-gray-900">Estimate Review</h2>
            <p className="text-sm text-gray-600 mt-1">
              {lines.length} lines • Click unit cost to edit
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
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 p-6">
        {/* Estimate Lines Table */}
        <div className="lg:col-span-3">
          <div className="overflow-x-auto max-h-96">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Line
                  </th>
                  <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Unit Cost
                  </th>
                  <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-3 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Extended Cost
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {lines.map((row) => {
                  const line = row.merged;
                  const optimistic = optimisticUpdates[line.id];
                  const displayLine = optimistic ? { ...line, ...optimistic } : line;
                  
                  // Use quantity from takeoff item if available, fallback to 1
                  const quantity = displayLine.takeoff_item_id ? displayLine.qty : (displayLine.qty || 1);
                  const unitCost = displayLine.unit_cost || 0;
                  const extendedCost = quantity * unitCost;
                  
                  return (
                    <tr key={line.id} className={`${hasOverrides(row) ? 'bg-yellow-50' : ''} ${pending ? 'opacity-50' : ''}`}>
                      {/* Line Description */}
                      <td className="px-3 xl:px-6 py-4">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{displayLine.description}</div>
                          {hasOverrides(row) && (
                            <div className="text-xs text-yellow-600">Modified</div>
                          )}
                        </div>
                      </td>

                      {/* Unit Cost - Editable */}
                      <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                        {isEditing(line.id, 'unit_cost') ? (
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
                            onClick={() => startEditing(line.id, 'unit_cost', displayLine.unit_cost)}
                            className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                          >
                            ${displayLine.unit_cost.toFixed(2)}
                          </div>
                        )}
                      </td>

                      {/* Quantity - Read-only */}
                      <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{quantity}</div>
                        {displayLine.takeoff_item_id && (
                          <div className="text-xs text-gray-500">From takeoff</div>
                        )}
                      </td>

                      {/* Extended Cost - Computed */}
                      <td className="px-3 xl:px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ${extendedCost.toFixed(2)}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Markups Panel */}
        <div className="lg:col-span-1">
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-4">Markups</h3>
            
            <div className="space-y-4">
              {/* Overhead */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Overhead %
                </label>
                {isMarkupEditing('overhead_pct') ? (
                  <input
                    ref={markupInputRef}
                    type="number"
                    step="0.1"
                    min="0"
                    max="30"
                    value={markupEditing.value}
                    onChange={(e) => setMarkupEditing(prev => ({ ...prev, value: e.target.value }))}
                    onKeyDown={handleMarkupKeyDown}
                    onBlur={handleMarkupBlur}
                    disabled={pending}
                    className="w-full px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                ) : (
                  <div
                    onClick={() => startMarkupEditing('overhead_pct', getDisplayMarkup('overhead_pct'))}
                    className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    {getDisplayMarkup('overhead_pct').toFixed(1)}%
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-1">
                  ${totals.overheadAmount.toFixed(2)}
                </div>
              </div>

              {/* Profit */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Profit %
                </label>
                {isMarkupEditing('profit_pct') ? (
                  <input
                    ref={markupInputRef}
                    type="number"
                    step="0.1"
                    min="0"
                    max="30"
                    value={markupEditing.value}
                    onChange={(e) => setMarkupEditing(prev => ({ ...prev, value: e.target.value }))}
                    onKeyDown={handleMarkupKeyDown}
                    onBlur={handleMarkupBlur}
                    disabled={pending}
                    className="w-full px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                ) : (
                  <div
                    onClick={() => startMarkupEditing('profit_pct', getDisplayMarkup('profit_pct'))}
                    className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    {getDisplayMarkup('profit_pct').toFixed(1)}%
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-1">
                  ${totals.profitAmount.toFixed(2)}
                </div>
              </div>

              {/* Contingency */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Contingency %
                </label>
                {isMarkupEditing('contingency_pct') ? (
                  <input
                    ref={markupInputRef}
                    type="number"
                    step="0.1"
                    min="0"
                    max="30"
                    value={markupEditing.value}
                    onChange={(e) => setMarkupEditing(prev => ({ ...prev, value: e.target.value }))}
                    onKeyDown={handleMarkupKeyDown}
                    onBlur={handleMarkupBlur}
                    disabled={pending}
                    className="w-full px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                ) : (
                  <div
                    onClick={() => startMarkupEditing('contingency_pct', getDisplayMarkup('contingency_pct'))}
                    className={`text-sm text-gray-900 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded min-h-[28px] flex items-center ${pending ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    {getDisplayMarkup('contingency_pct').toFixed(1)}%
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-1">
                  ${totals.contingencyAmount.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Totals */}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Subtotal:</span>
                  <span className="font-medium">${totals.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Markup:</span>
                  <span className="font-medium">{totals.totalMarkup.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-gray-200">
                  <span className="font-semibold text-gray-900">Grand Total:</span>
                  <span className="font-bold text-lg text-gray-900">${totals.grandTotal.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Toast notifications */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((toast, index) => (
          <div
            key={`${toast.itemId || 'markup'}-${index}`}
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
