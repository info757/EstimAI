import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getEstimateReview, 
  patchEstimateReview, 
  pipelineSync, 
  fileUrl 
} from '../api/client';
import type { ReviewRow, Patch } from '../types/api';
import ReviewTable from '../components/ReviewTable';
import { useToast } from '../context/ToastContext';

export default function ReviewEstimatePage() {
  const { pid } = useParams<{ pid: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  // State
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [edited, setEdited] = useState<Record<string, Record<string, any>>>({}); // {id: {key:value}}
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [recalc, setRecalc] = useState(false);

  // Fetch review data on mount
  useEffect(() => {
    if (!pid) return;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getEstimateReview(pid);
        setRows(response.rows);
      } catch (err) {
        console.error('Failed to load review data:', err);
        // Could add error state here if needed
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [pid]);

  // onChange handler for ReviewTable
  const handleChange = (id: string, key: string, value: any) => {
    setEdited(prev => ({ 
      ...prev, 
      [id]: { 
        ...prev[id], 
        [key]: value 
      } 
    }));
  };

  // Build patches from edited state
  const buildPatches = (): Patch[] => {
    return Object.entries(edited).map(([id, fields]) => ({
      id,
      fields,
      by: "will",
      reason: "manual review",
      at: new Date().toISOString(),
    }));
  };

  // Save overrides
  const saveOverrides = async () => {
    if (!pid) return;
    
    setSaving(true);
    try {
      const patches = buildPatches();
      if (patches.length) {
        await patchEstimateReview(pid, patches);
      }
      
      // Refetch review data
      const fresh = await getEstimateReview(pid);
      setRows(fresh.rows);
      setEdited({});
      
      // Show success toast
      toast('Saved overrides', { type: 'success' });
    } catch (err) {
      console.error('Failed to save overrides:', err);
      toast('Failed to save overrides', { type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  // Recalculate pipeline
  const handleRecalc = async () => {
    if (!pid) return;
    
    setRecalc(true);
    try {
      const res = await pipelineSync(pid);
      
      // Show success toast with PDF link
      const pdfUrl = fileUrl(res.pdf_path);
      toast('Recalculated. PDF ready', { 
        type: 'success',
        link: pdfUrl,
        label: 'Open PDF'
      });
      
      // Navigate back to project
      navigate(`/projects/${pid}`);
    } catch (err) {
      console.error('Failed to recalculate pipeline:', err);
      toast('Failed to recalculate pipeline', { type: 'error' });
    } finally {
      setRecalc(false);
    }
  };

  // Custom diff function for estimate fields
  const getEstimateDiff = (ai: any, edited: any): string => {
    if (typeof ai === 'number' && typeof edited === 'number') {
      const diff = edited - ai;
      return diff > 0 ? `+${diff}` : diff.toString();
    }
    return '';
  };

  // Calculate totals for rows if they exist
  const calculateTotals = (row: ReviewRow): Record<string, any> => {
    const totals: Record<string, any> = {};
    
    // If we have qty and unit_cost, calculate total
    if (row.merged.qty && row.merged.unit_cost) {
      const aiQty = row.ai.qty || 0;
      const aiUnitCost = row.ai.unit_cost || 0;
      const editedQty = edited[row.id]?.qty || row.merged.qty;
      const editedUnitCost = edited[row.id]?.unit_cost || row.merged.unit_cost;
      
      totals.ai_total = aiQty * aiUnitCost;
      totals.edited_total = editedQty * editedUnitCost;
      
      if (totals.ai_total !== totals.edited_total) {
        totals.total_diff = totals.edited_total - totals.ai_total;
      }
    }
    
    return totals;
  };

  if (loading) {
    return (
      <div className="p-4 flex justify-center items-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading review data...</span>
      </div>
    );
  }

  const hasEdits = Object.keys(edited).length > 0;

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Estimate Review - Project {pid}</h1>
        <div className="space-x-2">
          <button
            onClick={saveOverrides}
            disabled={!hasEdits || saving || recalc}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Overrides'}
          </button>
          <button
            onClick={handleRecalc}
            disabled={saving || recalc}
            className="px-4 py-2 bg-green-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {recalc ? 'Recalculating...' : 'Recalculate'}
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="text-gray-500 text-center py-8">
          No estimate data available for review.
        </div>
      ) : (
        <div>
          <ReviewTable
            rows={rows}
            editableKeys={["unit_cost", "overhead", "profit", "contingency"]}
            onChange={handleChange}
            confidenceKey="confidence"
            editedValues={edited}
            getDiff={getEstimateDiff}
          />
          
          {/* Totals summary if we have data */}
          {rows.some(row => row.merged.qty && row.merged.unit_cost) && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-3">Totals Summary</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {rows.map(row => {
                  const totals = calculateTotals(row);
                  if (Object.keys(totals).length === 0) return null;
                  
                  return (
                    <div key={row.id} className="p-3 bg-white rounded border">
                      <div className="font-medium text-sm text-gray-600">{row.id}</div>
                      <div className="text-sm">
                        <span className="text-gray-500">AI Total: </span>
                        <span className="font-medium">${totals.ai_total?.toFixed(2) || '0.00'}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-500">Edited Total: </span>
                        <span className="font-medium">${totals.edited_total?.toFixed(2) || '0.00'}</span>
                      </div>
                      {totals.total_diff !== undefined && (
                        <div className={`text-sm font-medium ${
                          totals.total_diff > 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          Δ: {totals.total_diff > 0 ? '+' : ''}${totals.total_diff.toFixed(2)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
