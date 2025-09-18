/**
 * EstimateTable - Unit tests for totals computation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EstimateTable from './EstimateTable';
import type { EstimateLine } from '../types/review';

// Mock the API client
vi.mock('../api/reviewClient', () => ({
  updateEstimateLines: vi.fn(),
  updateEstimateMarkups: vi.fn(),
}));

describe('EstimateTable - Totals Computation', () => {
  const mockLines = [
    {
      id: 'line1',
      ai: {
        id: 'line1',
        description: 'Concrete Foundation',
        unit: 'CY',
        quantity: 10,
        unit_cost: 150.00,
        extended_cost: 1500.00,
        takeoff_item_id: 'takeoff1'
      },
      override: undefined,
      merged: {
        id: 'line1',
        description: 'Concrete Foundation',
        unit: 'CY',
        quantity: 10,
        unit_cost: 150.00,
        extended_cost: 1500.00,
        takeoff_item_id: 'takeoff1'
      },
      confidence: 0.8
    },
    {
      id: 'line2',
      ai: {
        id: 'line2',
        description: 'Steel Rebar',
        unit: 'LB',
        quantity: 500,
        unit_cost: 2.50,
        extended_cost: 1250.00,
        takeoff_item_id: 'takeoff2'
      },
      override: undefined,
      merged: {
        id: 'line2',
        description: 'Steel Rebar',
        unit: 'LB',
        quantity: 500,
        unit_cost: 2.50,
        extended_cost: 1250.00,
        takeoff_item_id: 'takeoff2'
      },
      confidence: 0.9
    },
    {
      id: 'line3',
      ai: {
        id: 'line3',
        description: 'Labor',
        unit: 'HR',
        quantity: 1,
        unit_cost: 75.00,
        extended_cost: 75.00,
        takeoff_item_id: undefined // No takeoff item, uses line quantity
      },
      override: undefined,
      merged: {
        id: 'line3',
        description: 'Labor',
        unit: 'HR',
        quantity: 1,
        unit_cost: 75.00,
        extended_cost: 75.00,
        takeoff_item_id: undefined
      },
      confidence: 0.7
    }
  ];

  const mockMarkups = {
    overhead_pct: 10.0,
    profit_pct: 5.0,
    contingency_pct: 3.0
  };

  const mockOnEditLine = vi.fn();
  const mockOnEditMarkups = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('computes totals correctly with takeoff quantities and markups', () => {
    render(
      <EstimateTable
        lines={mockLines}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Expected calculations:
    // Line 1: 10 CY × $150.00 = $1,500.00
    // Line 2: 500 LB × $2.50 = $1,250.00  
    // Line 3: 1 HR × $75.00 = $75.00
    // Subtotal: $2,825.00
    // Overhead (10%): $282.50
    // Profit (5%): $141.25
    // Contingency (3%): $84.75
    // Total Markup: 18%
    // Grand Total: $2,825.00 × 1.18 = $3,333.50

    expect(screen.getByText('$2,825.00')).toBeInTheDocument(); // Subtotal
    expect(screen.getByText('18.0%')).toBeInTheDocument(); // Total Markup
    expect(screen.getByText('$3,333.50')).toBeInTheDocument(); // Grand Total
  });

  it('shows individual markup amounts correctly', () => {
    render(
      <EstimateTable
        lines={mockLines}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Check individual markup amounts
    expect(screen.getByText('$282.50')).toBeInTheDocument(); // Overhead amount
    expect(screen.getByText('$141.25')).toBeInTheDocument(); // Profit amount
    expect(screen.getByText('$84.75')).toBeInTheDocument(); // Contingency amount
  });

  it('updates totals optimistically when unit cost changes', async () => {
    render(
      <EstimateTable
        lines={mockLines}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first unit cost to edit it
    const unitCostCell = screen.getByText('$150.00');
    fireEvent.click(unitCostCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('150');
    fireEvent.change(input, { target: { value: '200' } });
    fireEvent.blur(input);

    // Check that totals update optimistically
    await waitFor(() => {
      // New calculations with $200 unit cost:
      // Line 1: 10 CY × $200.00 = $2,000.00
      // Line 2: 500 LB × $2.50 = $1,250.00
      // Line 3: 1 HR × $75.00 = $75.00
      // Subtotal: $3,325.00
      // Grand Total: $3,325.00 × 1.18 = $3,923.50
      expect(screen.getByText('$3,325.00')).toBeInTheDocument(); // New subtotal
      expect(screen.getByText('$3,923.50')).toBeInTheDocument(); // New grand total
    });
  });

  it('updates totals optimistically when markups change', async () => {
    render(
      <EstimateTable
        lines={mockLines}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on overhead percentage to edit it
    const overheadCell = screen.getByText('10.0%');
    fireEvent.click(overheadCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '15' } });
    fireEvent.blur(input);

    // Check that totals update optimistically
    await waitFor(() => {
      // New calculations with 15% overhead:
      // Subtotal: $2,825.00
      // Overhead (15%): $423.75
      // Profit (5%): $141.25
      // Contingency (3%): $84.75
      // Total Markup: 23%
      // Grand Total: $2,825.00 × 1.23 = $3,474.75
      expect(screen.getByText('$423.75')).toBeInTheDocument(); // New overhead amount
      expect(screen.getByText('23.0%')).toBeInTheDocument(); // New total markup
      expect(screen.getByText('$3,474.75')).toBeInTheDocument(); // New grand total
    });
  });

  it('handles zero quantities correctly', () => {
    const linesWithZeroQuantity = [
      {
        id: 'line1',
        ai: {
          id: 'line1',
          description: 'Zero Quantity Item',
          unit: 'EA',
          quantity: 0,
          unit_cost: 100.00,
          extended_cost: 0.00,
          takeoff_item_id: 'takeoff1'
        },
        override: undefined,
        merged: {
          id: 'line1',
          description: 'Zero Quantity Item',
          unit: 'EA',
          quantity: 0,
          unit_cost: 100.00,
          extended_cost: 0.00,
          takeoff_item_id: 'takeoff1'
        },
        confidence: 0.8
      }
    ];

    render(
      <EstimateTable
        lines={linesWithZeroQuantity}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // With zero quantity, all totals should be zero
    expect(screen.getByText('$0.00')).toBeInTheDocument(); // Subtotal
    expect(screen.getByText('$0.00')).toBeInTheDocument(); // Grand Total
  });

  it('handles missing takeoff_item_id by using line quantity', () => {
    const linesWithoutTakeoff = [
      {
        id: 'line1',
        ai: {
          id: 'line1',
          description: 'No Takeoff Item',
          unit: 'EA',
          quantity: 5,
          unit_cost: 50.00,
          extended_cost: 250.00,
          takeoff_item_id: undefined
        },
        override: undefined,
        merged: {
          id: 'line1',
          description: 'No Takeoff Item',
          unit: 'EA',
          quantity: 5,
          unit_cost: 50.00,
          extended_cost: 250.00,
          takeoff_item_id: undefined
        },
        confidence: 0.8
      }
    ];

    render(
      <EstimateTable
        lines={linesWithoutTakeoff}
        markups={mockMarkups}
        onEditLine={mockOnEditLine}
        onEditMarkups={mockOnEditMarkups}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Should use line quantity (5) instead of takeoff quantity
    // 5 EA × $50.00 = $250.00
    expect(screen.getByText('$250.00')).toBeInTheDocument(); // Subtotal
    expect(screen.getByText('$295.00')).toBeInTheDocument(); // Grand Total (250 × 1.18)
  });
});
