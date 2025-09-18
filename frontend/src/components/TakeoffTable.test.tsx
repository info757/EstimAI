/**
 * TakeoffTable - Component tests for optimistic updates
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TakeoffTable from './TakeoffTable';
import type { TakeoffItem } from '../types/review';

// Mock the API client
vi.mock('../api/reviewClient', () => ({
  updateTakeoffItems: vi.fn(),
}));

describe('TakeoffTable - Optimistic Updates', () => {
  const mockItems = [
    {
      id: 'item1',
      ai: {
        id: 'item1',
        description: 'Concrete Foundation',
        unit: 'CY',
        quantity: 10,
        cost_code: '03300',
        confidence: 0.8
      },
      override: undefined,
      merged: {
        id: 'item1',
        description: 'Concrete Foundation',
        unit: 'CY',
        quantity: 10,
        cost_code: '03300',
        confidence: 0.8
      },
      confidence: 0.8
    },
    {
      id: 'item2',
      ai: {
        id: 'item2',
        description: 'Steel Rebar',
        unit: 'LB',
        quantity: 500,
        cost_code: '03200',
        confidence: 0.9
      },
      override: undefined,
      merged: {
        id: 'item2',
        description: 'Steel Rebar',
        unit: 'LB',
        quantity: 500,
        cost_code: '03200',
        confidence: 0.9
      },
      confidence: 0.9
    }
  ];

  const mockOnEdit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows optimistic updates immediately when editing quantity', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '15' } });
    fireEvent.blur(input);

    // Check that the optimistic update is shown immediately
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    // Verify the onEdit callback was called
    expect(mockOnEdit).toHaveBeenCalledWith('item1', { quantity: 15 });
  });

  it('shows optimistic updates immediately when editing description', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first description to edit it
    const descriptionCell = screen.getByText('Concrete Foundation');
    fireEvent.click(descriptionCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('Concrete Foundation');
    fireEvent.change(input, { target: { value: 'Modified Concrete Foundation' } });
    fireEvent.blur(input);

    // Check that the optimistic update is shown immediately
    await waitFor(() => {
      expect(screen.getByText('Modified Concrete Foundation')).toBeInTheDocument();
    });

    // Verify the onEdit callback was called
    expect(mockOnEdit).toHaveBeenCalledWith('item1', { description: 'Modified Concrete Foundation' });
  });

  it('shows optimistic updates immediately when editing cost code', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first cost code to edit it
    const costCodeCell = screen.getByText('03300');
    fireEvent.click(costCodeCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('03300');
    fireEvent.change(input, { target: { value: '03400' } });
    fireEvent.blur(input);

    // Check that the optimistic update is shown immediately
    await waitFor(() => {
      expect(screen.getByText('03400')).toBeInTheDocument();
    });

    // Verify the onEdit callback was called
    expect(mockOnEdit).toHaveBeenCalledWith('item1', { cost_code: '03400' });
  });

  it('reverts optimistic updates when API call fails', async () => {
    // Mock the onEdit to reject
    mockOnEdit.mockRejectedValueOnce(new Error('API Error'));

    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '15' } });
    fireEvent.blur(input);

    // Initially shows optimistic update
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    // After API failure, should revert to original value
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Should not show the optimistic value anymore
    expect(screen.queryByText('15')).not.toBeInTheDocument();
  });

  it('shows dirty indicator when there are optimistic updates', () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={true}
      />
    );

    // Should show the dirty indicator
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  });

  it('does not show dirty indicator when there are no optimistic updates', () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Should not show the dirty indicator
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
  });

  it('disables editing when pending is true', () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={true}
        hasDirtyEdits={false}
      />
    );

    // Try to click on a quantity cell
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Should not show input field when pending
    expect(screen.queryByDisplayValue('10')).not.toBeInTheDocument();
  });

  it('shows pending state visually when pending is true', () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={true}
        hasDirtyEdits={false}
      />
    );

    // Check that rows have opacity-50 class (pending state)
    const rows = screen.getAllByRole('row');
    // Skip header row (index 0)
    rows.slice(1).forEach(row => {
      expect(row).toHaveClass('opacity-50');
    });
  });

  it('handles Enter key to commit changes', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '15' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Check that the optimistic update is shown
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    // Verify the onEdit callback was called
    expect(mockOnEdit).toHaveBeenCalledWith('item1', { quantity: 15 });
  });

  it('handles Escape key to cancel editing', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and change the value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '15' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    // Should revert to original value without calling onEdit
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    // Should not call onEdit when cancelled
    expect(mockOnEdit).not.toHaveBeenCalled();
  });

  it('validates numeric input and shows error for invalid values', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and enter an invalid value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: 'invalid' } });
    fireEvent.blur(input);

    // Should show error toast
    await waitFor(() => {
      expect(screen.getByText('quantity: Must be a valid number')).toBeInTheDocument();
    });

    // Should not call onEdit for invalid input
    expect(mockOnEdit).not.toHaveBeenCalled();
  });

  it('clamps negative quantities to zero', async () => {
    render(
      <TakeoffTable
        items={mockItems}
        onEdit={mockOnEdit}
        loading={false}
        pending={false}
        hasDirtyEdits={false}
      />
    );

    // Find and click on the first quantity to edit it
    const quantityCell = screen.getByText('10');
    fireEvent.click(quantityCell);

    // Find the input and enter a negative value
    const input = screen.getByDisplayValue('10');
    fireEvent.change(input, { target: { value: '-5' } });
    fireEvent.blur(input);

    // Should show clamping error toast
    await waitFor(() => {
      expect(screen.getByText('quantity: Clamped to minimum value of 0')).toBeInTheDocument();
    });

    // Should not call onEdit for clamped value
    expect(mockOnEdit).not.toHaveBeenCalled();
  });
});
