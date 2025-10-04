import React, { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface CountItem {
  id: string;
  file: string;
  page: number;
  type: string;
  confidence: number;
  x_pdf: number;
  y_pdf: number;
  points_per_foot: number;
  status: "pending" | "accepted" | "rejected" | "edited";
  reviewer_note?: string | null;
  type_edited?: string | null;
  x_pdf_edited?: number | null;
  y_pdf_edited?: number | null;
  attributes?: Record<string, any>;
  quantity?: number;
  unit?: string;
  name?: string;
  subtype?: string;
}

export interface QAFlag {
  code: string;
  message: string;
  geom_id?: string;
  sheet_ref?: string;
}

export interface ReviewTableProps {
  file: string;
  page: number;
  onRefresh?: () => void;
  onCommit?: (report: any) => void;
}

export default function ReviewTable({ file, page, onRefresh, onCommit }: ReviewTableProps) {
  const [rows, setRows] = useState<CountItem[]>([]);
  const [qaFlags, setQaFlags] = useState<QAFlag[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");

  // Load data on mount and when file/page changes
  useEffect(() => {
    if (file) {
      loadData();
    }
  }, [file, page]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load count items
      const countsRes = await fetch(`${API}/v1/counts?file=${encodeURIComponent(file)}&page=${page}`);
      const counts = await countsRes.json();
      setRows(counts);

      // Load QA flags if available
      try {
        const qaRes = await fetch(`${API}/v1/counts/assemblies?file=${encodeURIComponent(file)}&page=${page}&include_pricing=false`);
        const qaData = await qaRes.json();
        if (qaData.summary && qaData.summary.qa_flags) {
          setQaFlags(qaData.summary.qa_flags);
        }
      } catch (error) {
        console.log("QA flags not available:", error);
        setQaFlags([]);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const patchItem = async (id: string, patch: Partial<CountItem>) => {
    // Optimistic update
    setRows(prev => prev.map(r => r.id === id ? { ...r, ...patch } : r));
    
    try {
      await fetch(`${API}/v1/counts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch)
      });
    } catch (error) {
      console.error("Error patching item:", error);
      // Revert optimistic update on error
      loadData();
    }
  };

  const handleStatusChange = (id: string, status: CountItem["status"]) => {
    patchItem(id, { status });
  };

  const handleTypeChange = (id: string, type: string) => {
    patchItem(id, { type_edited: type, status: "edited" });
  };

  const handleNoteChange = (id: string, note: string) => {
    patchItem(id, { reviewer_note: note });
  };

  const handleCoordinateChange = (id: string, field: 'x_pdf_edited' | 'y_pdf_edited', value: number) => {
    patchItem(id, { [field]: value, status: "edited" });
  };

  const handleSelectRow = (id: string, selected: boolean) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(id);
      } else {
        newSet.delete(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedRows(new Set(filteredRows.map(r => r.id)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleBulkStatusChange = (status: CountItem["status"]) => {
    selectedRows.forEach(id => {
      patchItem(id, { status });
    });
    setSelectedRows(new Set());
  };

  const handleCommit = async () => {
    setIsCommitting(true);
    try {
      const res = await fetch(`${API}/v1/review/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          file, 
          pages: [page], 
          threshold: 0.8 
        })
      });
      
      if (res.ok) {
        const reportData = await res.json();
        setReport(reportData);
        onCommit?.(reportData);
      } else {
        const error = await res.text();
        alert(`Commit failed: ${error}`);
      }
    } catch (error) {
      console.error("Error committing:", error);
      alert(`Commit error: ${error}`);
    } finally {
      setIsCommitting(false);
    }
  };

  const getStatusBadge = (status: CountItem["status"]) => {
    const styles = {
      pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
      accepted: "bg-green-100 text-green-800 border-green-200",
      rejected: "bg-red-100 text-red-800 border-red-200",
      edited: "bg-blue-100 text-blue-800 border-blue-200"
    };
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status]}`}>
        {status}
      </span>
    );
  };

  const getQAFlagBadge = (item: CountItem) => {
    // Find QA flags for this item
    const itemFlags = qaFlags.filter(flag => 
      flag.geom_id === item.id || 
      (flag.sheet_ref && flag.sheet_ref.includes(item.file))
    );

    if (itemFlags.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-1">
        {itemFlags.map((flag, index) => (
          <span
            key={index}
            className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800 border border-orange-200"
            title={flag.message}
          >
            {flag.code}
          </span>
        ))}
      </div>
    );
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-600";
    if (confidence >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  // Filter rows based on current filters
  const filteredRows = rows.filter(row => {
    if (filterStatus !== "all" && row.status !== filterStatus) return false;
    if (filterType !== "all" && !row.type.toLowerCase().includes(filterType.toLowerCase())) return false;
    return true;
  });

  const stats = {
    total: rows.length,
    pending: rows.filter(r => r.status === "pending").length,
    accepted: rows.filter(r => r.status === "accepted").length,
    rejected: rows.filter(r => r.status === "rejected").length,
    edited: rows.filter(r => r.status === "edited").length
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats and Controls */}
      <div className="bg-gray-50 p-4 rounded-lg border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold">Review Items</h3>
            <div className="flex space-x-2 text-sm">
              <span className="text-gray-600">Total: {stats.total}</span>
              <span className="text-yellow-600">Pending: {stats.pending}</span>
              <span className="text-green-600">Accepted: {stats.accepted}</span>
              <span className="text-red-600">Rejected: {stats.rejected}</span>
              <span className="text-blue-600">Edited: {stats.edited}</span>
            </div>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={loadData}
              className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Refresh
            </button>
            <button
              onClick={handleCommit}
              disabled={isCommitting}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
            >
              {isCommitting ? "Committing..." : "Commit Review"}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium">Status:</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
              <option value="edited">Edited</option>
            </select>
          </div>
          
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium">Type:</label>
            <input
              type="text"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              placeholder="Filter by type..."
              className="text-sm border rounded px-2 py-1"
            />
          </div>

          {selectedRows.size > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">{selectedRows.size} selected</span>
              <button
                onClick={() => handleBulkStatusChange("accepted")}
                className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
              >
                Accept All
              </button>
              <button
                onClick={() => handleBulkStatusChange("rejected")}
                className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reject All
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">
                <input
                  type="checkbox"
                  checked={selectedRows.size === filteredRows.length && filteredRows.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Type</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Confidence</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Location (ft)</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Quantity</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">QA Flags</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  No items found. {!file ? "Please select a file first." : "Try adjusting your filters."}
                </td>
              </tr>
            ) : (
              filteredRows.map((row) => {
                const xft = (row.x_pdf / row.points_per_foot).toFixed(2);
                const yft = (row.y_pdf / row.points_per_foot).toFixed(2);
                const isSelected = selectedRows.has(row.id);

                return (
                  <tr key={row.id} className={isSelected ? "bg-blue-50" : "hover:bg-gray-50"}>
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => handleSelectRow(row.id, e.target.checked)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={row.status}
                        onChange={(e) => handleStatusChange(row.id, e.target.value as CountItem["status"])}
                        className="text-sm border rounded px-2 py-1"
                      >
                        <option value="pending">Pending</option>
                        <option value="accepted">Accepted</option>
                        <option value="rejected">Rejected</option>
                        <option value="edited">Edited</option>
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <input
                        value={row.type_edited ?? row.type}
                        onChange={(e) => handleTypeChange(row.id, e.target.value)}
                        className="text-sm border rounded px-2 py-1 w-full"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <span className={`text-sm font-medium ${getConfidenceColor(row.confidence)}`}>
                        {(row.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="text-sm">
                        <div>X: {xft} ft</div>
                        <div>Y: {yft} ft</div>
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="text-sm">
                        {row.quantity && (
                          <div>{row.quantity} {row.unit || ""}</div>
                        )}
                        {row.name && (
                          <div className="text-gray-600">{row.name}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      {getQAFlagBadge(row)}
                    </td>
                    <td className="px-4 py-2">
                      <input
                        value={row.reviewer_note ?? ""}
                        onChange={(e) => handleNoteChange(row.id, e.target.value)}
                        placeholder="Add note..."
                        className="text-sm border rounded px-2 py-1 w-full"
                      />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Report */}
      {report && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="font-semibold text-green-800 mb-2">Review Metrics</h4>
          <div className="text-sm text-green-700 space-y-1">
            <div>Total: {report.n_total} • TP: {report.n_tp} • FP: {report.n_fp} • FN: {report.n_fn}</div>
            <div>Precision: {(report.precision * 100).toFixed(1)}% • Recall: {(report.recall * 100).toFixed(1)}% • F1: {(report.f1 * 100).toFixed(1)}%</div>
            <div>MAE: {report.loc_mae_ft?.toFixed?.(2)} ft • P95: {report.loc_p95_ft?.toFixed?.(2)} ft</div>
            {report.export_csv_url && (
              <div className="mt-2">
                <a 
                  href={`${API}${report.export_csv_url}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  Download accepted.csv
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}