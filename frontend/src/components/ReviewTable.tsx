import React from 'react';
import type { ReviewRow } from '../types/api';

interface ReviewTableProps {
  rows: ReviewRow[];
  editableKeys: string[];
  onChange: (id: string, key: string, value: any) => void;
  getDiff?: (ai: any, edited: any) => string | number;
  confidenceKey?: string;
  editedValues?: Record<string, Record<string, any>>; // {id: {key: value}}
}

interface EditableValue {
  [key: string]: any;
}

export default function ReviewTable({ 
  rows, 
  editableKeys, 
  onChange, 
  getDiff, 
  confidenceKey = 'confidence',
  editedValues = {}
}: ReviewTableProps) {
  
  // Default diff function for numeric values
  const defaultGetDiff = (ai: any, edited: any): string => {
    if (typeof ai === 'number' && typeof edited === 'number') {
      const diff = edited - ai;
      return diff > 0 ? `+${diff}` : diff.toString();
    }
    return '';
  };

  const diffFunction = getDiff || defaultGetDiff;

  // Check if a value has been edited
  const isEdited = (aiValue: any, editedValue: any, rowId: string, key: string): boolean => {
    const userEditedValue = editedValues[rowId]?.[key];
    if (userEditedValue !== undefined) {
      return aiValue !== userEditedValue;
    }
    return aiValue !== editedValue;
  };

  // Get confidence display value
  const getConfidenceDisplay = (row: ReviewRow): string => {
    const confidence = row[confidenceKey as keyof ReviewRow];
    if (typeof confidence === 'number') {
      return `${(confidence * 100).toFixed(1)}%`;
    }
    return '-';
  };

  // Get confidence color class
  const getConfidenceColor = (row: ReviewRow): string => {
    const confidence = row[confidenceKey as keyof ReviewRow];
    if (typeof confidence === 'number') {
      if (confidence >= 0.8) return 'bg-green-100 text-green-800';
      if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
      return 'bg-red-100 text-red-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  if (rows.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        No data available for review.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            <th className="border px-4 py-2 text-left">ID</th>
            {editableKeys.map(key => (
              <th key={key} className="border px-4 py-2 text-center">
                {key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
              </th>
            ))}
            {confidenceKey && (
              <th className="border px-4 py-2 text-center">Confidence</th>
            )}
            <th className="border px-4 py-2 text-center">Δ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.id} className="hover:bg-gray-50">
              {/* ID Column */}
              <td className="border px-4 py-2 font-medium text-sm">
                {row.id}
              </td>
              
                             {/* Editable Value Columns */}
               {editableKeys.map(key => {
                 const aiValue = row.ai[key];
                 const editedValue = row.merged[key];
                 const isValueEdited = isEdited(aiValue, editedValue, row.id, key);
                
                return (
                  <td 
                    key={key} 
                    className={`border px-4 py-2 ${isValueEdited ? 'bg-yellow-50' : ''}`}
                  >
                    {/* AI Value (small, secondary) */}
                    <div className="text-xs text-gray-500 mb-1">
                      AI: {aiValue?.toString() || '-'}
                    </div>
                    
                    {/* Editable Input */}
                    <input
                      type={typeof aiValue === 'number' ? 'number' : 'text'}
                      value={editedValues[row.id]?.[key]?.toString() || editedValue?.toString() || ''}
                      onChange={(e) => onChange(row.id, key, e.target.value)}
                      className={`w-full px-2 py-1 text-sm border rounded ${
                        isValueEdited ? 'border-yellow-300 bg-yellow-50' : 'border-gray-300'
                      }`}
                      placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                    />
                  </td>
                );
              })}
              
              {/* Confidence Column */}
              {confidenceKey && (
                <td className="border px-4 py-2 text-center">
                  <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(row)}`}>
                    {getConfidenceDisplay(row)}
                  </span>
                </td>
              )}
              
              {/* Delta Column */}
              <td className="border px-4 py-2 text-center">
                {editableKeys.map(key => {
                  const aiValue = row.ai[key];
                  const editedValue = row.merged[key];
                  const diff = diffFunction(aiValue, editedValue);
                  
                  if (diff !== '' && diff !== 0) {
                    return (
                      <div key={key} className="text-xs">
                        <span className="font-medium">{key}:</span> {diff}
                      </div>
                    );
                  }
                  return null;
                }).filter(Boolean)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
