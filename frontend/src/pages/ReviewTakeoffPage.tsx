import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getTakeoffReview, 
  patchTakeoffReview, 
  pipelineSync, 
  fileUrl 
} from '../api/client';
import type { ReviewRow, Patch } from '../types/api';
import ReviewTable from '../components/ReviewTable';
import { useToast } from '../context/ToastContext';

export default function ReviewTakeoffPage() {
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
        const response = await getTakeoffReview(pid);
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
        await patchTakeoffReview(pid, patches);
      }
      
      // Refetch review data
      const fresh = await getTakeoffReview(pid);
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
        <h1 className="text-2xl font-bold">Takeoff Review - Project {pid}</h1>
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
          No takeoff data available for review.
        </div>
      ) : (
        <ReviewTable
          rows={rows}
          editableKeys={["qty", "unit", "desc", "cost_code"]}
          onChange={handleChange}
          confidenceKey="confidence"
          editedValues={edited}
        />
      )}
    </div>
  );
}
