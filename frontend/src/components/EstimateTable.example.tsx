/**
 * Example usage of EstimateTable component
 */

import React, { useState } from 'react';
import EstimateTable from './EstimateTable';
import type { EstimateLine } from '../types/review';

// Example data structure
const exampleEstimateData = [
  {
    id: 'line-001',
    ai: {
      id: 'line-001',
      description: 'Concrete slab 4" thick',
      unit: 'sq ft',
      quantity: 1200,
      unit_cost: 8.50,
      extended_cost: 10200.00,
      takeoff_item_id: 'item-001'
    },
    override: undefined,
    merged: {
      id: 'line-001',
      description: 'Concrete slab 4" thick',
      unit: 'sq ft',
      quantity: 1200,
      unit_cost: 8.50,
      extended_cost: 10200.00,
      takeoff_item_id: 'item-001'
    },
    confidence: 0.95
  },
  {
    id: 'line-002',
    ai: {
      id: 'line-002',
      description: 'Steel reinforcement #4 bars',
      unit: 'linear ft',
      quantity: 800,
      unit_cost: 2.25,
      extended_cost: 1800.00,
      takeoff_item_id: 'item-002'
    },
    override: {
      unit_cost: 2.50
    },
    merged: {
      id: 'line-002',
      description: 'Steel reinforcement #4 bars',
      unit: 'linear ft',
      quantity: 800,
      unit_cost: 2.50,
      extended_cost: 2000.00,
      takeoff_item_id: 'item-002'
    },
    confidence: 0.75
  },
  {
    id: 'line-003',
    ai: {
      id: 'line-003',
      description: 'Electrical conduit 1/2"',
      unit: 'linear ft',
      quantity: 500,
      unit_cost: 1.80,
      extended_cost: 900.00,
      takeoff_item_id: 'item-003'
    },
    override: undefined,
    merged: {
      id: 'line-003',
      description: 'Electrical conduit 1/2"',
      unit: 'linear ft',
      quantity: 500,
      unit_cost: 1.80,
      extended_cost: 900.00,
      takeoff_item_id: 'item-003'
    },
    confidence: 0.35
  },
  {
    id: 'line-004',
    ai: {
      id: 'line-004',
      description: 'Labor - General',
      unit: 'hours',
      quantity: 1, // No takeoff item linked, uses fallback quantity
      unit_cost: 75.00,
      extended_cost: 75.00
    },
    override: undefined,
    merged: {
      id: 'line-004',
      description: 'Labor - General',
      unit: 'hours',
      quantity: 1,
      unit_cost: 75.00,
      extended_cost: 75.00
    },
    confidence: 0.90
  }
];

const exampleMarkups = {
  overhead_pct: 12.0,
  profit_pct: 8.5,
  contingency_pct: 5.0
};

export default function EstimateTableExample() {
  const [lines, setLines] = useState(exampleEstimateData);
  const [markups, setMarkups] = useState(exampleMarkups);
  const [loading, setLoading] = useState(false);

  const handleEditLine = async (lineId: string, fields: { unit_cost?: number }) => {
    console.log('Editing line:', lineId, 'with fields:', fields);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Update local state (in real app, this would be handled by the parent component)
    setLines(prev => prev.map(line => {
      if (line.id === lineId) {
        const updatedLine = {
          ...line,
          override: { ...line.override, ...fields },
          merged: { ...line.merged, ...fields }
        };
        
        // Recalculate extended cost
        const quantity = updatedLine.merged.takeoff_item_id ? updatedLine.merged.quantity : 1;
        updatedLine.merged.extended_cost = quantity * (updatedLine.merged.unit_cost || 0);
        
        return updatedLine;
      }
      return line;
    }));
    
    console.log('Line updated successfully');
  };

  const handleEditMarkups = async (newMarkups: {
    overhead_pct?: number;
    profit_pct?: number;
    contingency_pct?: number;
  }) => {
    console.log('Editing markups:', newMarkups);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Update local state
    setMarkups(prev => ({ ...prev, ...newMarkups }));
    
    console.log('Markups updated successfully');
  };

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLines([...exampleEstimateData]);
      setMarkups({ ...exampleMarkups });
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">EstimateTable Example</h1>
        <p className="text-gray-600 mt-1">
          This demonstrates the EstimateTable component with inline editing and real-time calculations.
        </p>
        <button
          onClick={handleRefresh}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh Data
        </button>
      </div>

      <EstimateTable
        lines={lines}
        markups={markups}
        onEditLine={handleEditLine}
        onEditMarkups={handleEditMarkups}
        loading={loading}
      />

      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold text-gray-900 mb-2">Usage Instructions:</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• <strong>Click unit cost</strong> to edit pricing for any line</li>
          <li>• <strong>Click markup percentages</strong> to adjust overhead, profit, contingency</li>
          <li>• <strong>Press Enter</strong> to save changes</li>
          <li>• <strong>Press Escape</strong> to cancel editing</li>
          <li>• <strong>Click outside</strong> (onBlur) to save changes</li>
          <li>• <strong>Extended costs</strong> are calculated automatically (quantity × unit cost)</li>
          <li>• <strong>Quantities</strong> come from linked takeoff items or default to 1</li>
          <li>• <strong>Totals update</strong> in real-time as you make changes</li>
          <li>• <strong>Toast notifications</strong> show save success/failure</li>
        </ul>
      </div>

      <div className="mt-4 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">Key Features:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Client-side calculations</strong> - All totals update instantly</li>
          <li>• <strong>Optimistic updates</strong> - UI responds immediately while saving</li>
          <li>• <strong>Linked takeoff items</strong> - Quantities pulled from takeoff data</li>
          <li>• <strong>Markup panel</strong> - Side panel for adjusting percentages</li>
          <li>• <strong>Real-time totals</strong> - Subtotal, markups, and grand total</li>
          <li>• <strong>Responsive design</strong> - Works on desktop and mobile</li>
        </ul>
      </div>
    </div>
  );
}
