/**
 * Example usage of TakeoffTable component
 */

import React, { useState } from 'react';
import TakeoffTable from './TakeoffTable';
import type { TakeoffItem } from '../types/review';

// Example data structure
const exampleTakeoffData = [
  {
    id: 'item-001',
    ai: {
      id: 'item-001',
      description: 'Concrete slab 4" thick',
      unit: 'sq ft',
      quantity: 1200,
      cost_code: 'C-001',
      confidence: 0.95
    },
    override: undefined,
    merged: {
      id: 'item-001',
      description: 'Concrete slab 4" thick',
      unit: 'sq ft',
      quantity: 1200,
      cost_code: 'C-001',
      confidence: 0.95
    },
    confidence: 0.95
  },
  {
    id: 'item-002',
    ai: {
      id: 'item-002',
      description: 'Steel reinforcement #4 bars',
      unit: 'linear ft',
      quantity: 800,
      cost_code: 'S-001',
      confidence: 0.75
    },
    override: {
      quantity: 850,
      cost_code: 'S-002'
    },
    merged: {
      id: 'item-002',
      description: 'Steel reinforcement #4 bars',
      unit: 'linear ft',
      quantity: 850,
      cost_code: 'S-002',
      confidence: 0.75
    },
    confidence: 0.75
  },
  {
    id: 'item-003',
    ai: {
      id: 'item-003',
      description: 'Electrical conduit 1/2"',
      unit: 'linear ft',
      quantity: 500,
      cost_code: 'E-001',
      confidence: 0.35
    },
    override: undefined,
    merged: {
      id: 'item-003',
      description: 'Electrical conduit 1/2"',
      unit: 'linear ft',
      quantity: 500,
      cost_code: 'E-001',
      confidence: 0.35
    },
    confidence: 0.35
  }
];

export default function TakeoffTableExample() {
  const [items, setItems] = useState(exampleTakeoffData);
  const [loading, setLoading] = useState(false);

  const handleEdit = async (itemId: string, fields: Partial<TakeoffItem>) => {
    console.log('Editing item:', itemId, 'with fields:', fields);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Update local state (in real app, this would be handled by the parent component)
    setItems(prev => prev.map(item => {
      if (item.id === itemId) {
        return {
          ...item,
          override: { ...item.override, ...fields },
          merged: { ...item.merged, ...fields }
        };
      }
      return item;
    }));
    
    console.log('Item updated successfully');
  };

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setItems([...exampleTakeoffData]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">TakeoffTable Example</h1>
        <p className="text-gray-600 mt-1">
          This demonstrates the TakeoffTable component with inline editing capabilities.
        </p>
        <button
          onClick={handleRefresh}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh Data
        </button>
      </div>

      <TakeoffTable
        items={items}
        onEdit={handleEdit}
        loading={loading}
      />

      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold text-gray-900 mb-2">Usage Instructions:</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• <strong>Click any field</strong> to start editing (Description, Quantity, Cost Code)</li>
          <li>• <strong>Press Enter</strong> to save changes</li>
          <li>• <strong>Press Escape</strong> to cancel editing</li>
          <li>• <strong>Click outside</strong> (onBlur) to save changes</li>
          <li>• <strong>Confidence badges</strong> show Low (&lt;40%), Med (40-70%), High (&gt;70%)</li>
          <li>• <strong>Yellow rows</strong> indicate items with overrides</li>
          <li>• <strong>Toast notifications</strong> show save success/failure</li>
        </ul>
      </div>
    </div>
  );
}
