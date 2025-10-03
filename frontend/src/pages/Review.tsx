import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Row = {
  id: string; file: string; page: number; type: string;
  confidence: number; x_pdf: number; y_pdf: number; points_per_foot: number;
  status: "pending" | "accepted" | "rejected" | "edited";
  reviewer_note?: string | null; type_edited?: string | null;
};

type Report = {
  n_total: number; n_tp: number; n_fp: number; n_fn: number;
  precision: number; recall: number; f1: number;
  loc_mae_ft: number; loc_p95_ft: number;
  export_csv_url?: string | null;
};

export default function Review() {
  const [params, setParams] = useSearchParams();
  const file = params.get("file") || "";
  const page = Number(params.get("page") || "1");
  const [rows, setRows] = useState<Row[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  console.log("Review component loaded", { file, page });

  async function refresh() {
    const res = await fetch(`${API}/v1/counts?file=${encodeURIComponent(file)}&page=${page}`);
    setRows(await res.json());
  }

  async function patch(id: string, patch: Partial<Row>) {
    setRows(prev => prev.map(r => r.id === id ? { ...r, ...patch } : r));
    await fetch(`${API}/v1/counts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch)
    });
  }

  async function commit() {
    const res = await fetch(`${API}/v1/review/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file, pages: [page], threshold: 0.8 })
    });
    setReport(await res.json());
  }

  async function runTakeoff() {
    if (!file) {
      alert("Please enter a file name first");
      return;
    }
    
    setIsRunning(true);
    try {
      const res = await fetch(`${API}/v1/detect?file=${encodeURIComponent(file)}&page=${page - 1}&points_per_foot=50.0`, {
        method: "POST"
      });
      if (res.ok) {
        await refresh(); // Refresh the data after detection
      } else {
        const error = await res.text();
        alert(`Detection failed: ${error}`);
      }
    } catch (error) {
      alert(`Detection error: ${error}`);
    } finally {
      setIsRunning(false);
    }
  }

  function setFile(newFile: string) {
    setParams({ file: newFile, page: page.toString() });
  }

  function setPage(newPage: number) {
    setParams({ file, page: newPage.toString() });
  }

  useEffect(() => { refresh(); }, [file, page]);

  return (
    <div style={{ padding: 16, maxWidth: 1100, margin: "0 auto" }}>
      <h2>Takeoff Review</h2>
      
      {/* File and Page Input */}
      <div style={{ marginBottom: 20, padding: 16, backgroundColor: "#f8fafc", borderRadius: 8, border: "1px solid #e5e7eb" }}>
        <div style={{ marginBottom: 10 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>File:</label>
          <input 
            type="text" 
            value={file} 
            onChange={e => setFile(e.target.value)}
            placeholder="e.g., 280-utility-construction-plans.pdf"
            style={{ width: "100%", padding: 8, border: "1px solid #d1d5db", borderRadius: 4 }}
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Page:</label>
          <input 
            type="number" 
            value={page} 
            onChange={e => setPage(Number(e.target.value))}
            min="1"
            style={{ width: 100, padding: 8, border: "1px solid #d1d5db", borderRadius: 4 }}
          />
        </div>
        <div>
          <button 
            onClick={runTakeoff} 
            disabled={isRunning || !file}
            style={{ 
              padding: "8px 16px", 
              backgroundColor: isRunning ? "#9ca3af" : "#3b82f6", 
              color: "white", 
              border: "none", 
              borderRadius: 4, 
              cursor: isRunning ? "not-allowed" : "pointer",
              marginRight: 8
            }}
          >
            {isRunning ? "Running..." : "Run Takeoff"}
          </button>
          <button onClick={refresh} style={{ padding: "8px 16px", backgroundColor: "#6b7280", color: "white", border: "none", borderRadius: 4, cursor: "pointer", marginRight: 8 }}>
            Refresh
          </button>
          <button onClick={commit} style={{ padding: "8px 16px", backgroundColor: "#10b981", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>
            Commit Review
          </button>
        </div>
      </div>

      <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead style={{ background: "#f8fafc" }}>
            <tr>
              <th style={th}>Status</th>
              <th style={th}>Type</th>
              <th style={th}>Conf</th>
              <th style={th}>X(ft)</th>
              <th style={th}>Y(ft)</th>
              <th style={th}>Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={6} style={{ padding: 10, textAlign: "center", color: "#64748b" }}>
                No rows yet. Click "Run Takeoff" in the header, then Refresh.
              </td></tr>
            )}
            {rows.map(r => {
              const xft = (r.x_pdf / r.points_per_foot).toFixed(2);
              const yft = (r.y_pdf / r.points_per_foot).toFixed(2);
              return (
                <tr key={r.id}>
                  <td style={td}>
                    <select value={r.status} onChange={e => patch(r.id, { status: e.target.value as Row["status"] })}>
                      <option>pending</option><option>accepted</option><option>rejected</option><option>edited</option>
                    </select>
                  </td>
                  <td style={td}>
                    <input value={r.type_edited ?? r.type}
                           onChange={e => patch(r.id, { type_edited: e.target.value, status: "edited" })} />
                  </td>
                  <td style={td}>{(r.confidence * 100).toFixed(0)}%</td>
                  <td style={td}>{xft}</td>
                  <td style={td}>{yft}</td>
                  <td style={td}>
                    <input value={r.reviewer_note ?? ""} onChange={e => patch(r.id, { reviewer_note: e.target.value })} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {report && (
        <div style={{ marginTop: 12, border: "1px solid #e5e7eb", borderRadius: 8, padding: 12 }}>
          <strong>Metrics</strong>
          <div style={{ marginTop: 6 }}>
            Total {report.n_total} • TP {report.n_tp} • FP {report.n_fp} • FN {report.n_fn}<br />
            Precision {(report.precision * 100).toFixed(1)}% • Recall {(report.recall * 100).toFixed(1)}% • F1 {(report.f1 * 100).toFixed(1)}%<br />
            MAE {report.loc_mae_ft?.toFixed?.(2)} ft • P95 {report.loc_p95_ft?.toFixed?.(2)} ft
          </div>
          {report.export_csv_url && (
            <div style={{ marginTop: 6 }}>
              <a href={`${API}${report.export_csv_url}`} target="_blank">Download accepted.csv</a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", borderBottom: "1px solid #e5e7eb" };
const td: React.CSSProperties = { padding: "6px 10px", borderBottom: "1px solid #f1f5f9" };
