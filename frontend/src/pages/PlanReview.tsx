import { useEffect, useMemo, useRef, useState } from "react";
import WebViewer from "@pdftron/webviewer";
import Header from "../components/Header";

// ----- types -----
type CountItem = {
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
  x_pdf_edited?: number | null;
  y_pdf_edited?: number | null;
  type_edited?: string | null;
};

type ReportOut = {
  n_total: number;
  n_tp: number;
  n_fp: number;
  n_fn: number;
  precision: number;
  recall: number;
  f1: number;
  loc_mae_ft: number;
  loc_p95_ft: number;
  export_csv_url?: string | null;
};

// ----- utils -----
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const getParam = (k: string, dflt: string) => new URLSearchParams(location.search).get(k) || dflt;
const fmtPct = (x: number) => (isFinite(x) ? (x * 100).toFixed(1) + "%" : "—");
const fmtNum = (x?: number) => (x ?? x === 0 ? x.toFixed(2) : "—");

// Local storage for calibration
const ppfKey = (file: string, page: number) => `ppf:${file}:${page}`;
const loadPPF = (file: string, page: number) => {
  const v = localStorage.getItem(ppfKey(file, page));
  return v ? Number(v) : NaN;
};
const savePPF = (file: string, page: number, ppf: number) =>
  localStorage.setItem(ppfKey(file, page), String(ppf));

// Jump helper (transient pulse)
async function jumpTo(instance: any, page: number, x_pdf: number, y_pdf: number) {
  if (!instance) return;
  const { documentViewer, Annotations, annotationManager, Math: WvMath } = instance.Core;
  documentViewer.setCurrentPage(page);
  const r = 10;
  const pulse = new Annotations.EllipseAnnotation();
  pulse.PageNumber = page;
  pulse.StrokeThickness = 3;
  pulse.StrokeColor = new Annotations.Color(0, 180, 255, 1);
  pulse.FillColor = new Annotations.Color(0, 180, 255, 0.2);
  pulse.ReadOnly = true;
  pulse.setRect(new WvMath.Rect(x_pdf - r, y_pdf - r, x_pdf + r, y_pdf + r));
  annotationManager.addAnnotation(pulse);
  annotationManager.redrawAnnotation(pulse);
  await new Promise((res) => setTimeout(res, 1200));
  annotationManager.deleteAnnotation(pulse, true, true);
}

// ----- Calibration banner -----
function CalibrationBanner({
  file,
  page,
  ppf,
  setPPF,
}: {
  file: string;
  page: number;
  ppf: number | undefined;
  setPPF: (v: number) => void;
}) {
  const [mode, setMode] = useState<"ratio" | "direct">("ratio");
  const [inchesPerFeet, setInchesPerFeet] = useState<number>(50); // 1"=50'
  const [ppfDirect, setPpfDirect] = useState<string>("");

  useEffect(() => {
    if (ppf && isFinite(ppf)) setPpfDirect(String(ppf));
  }, [ppf]);

  const computedPPF = useMemo(() => 72 / inchesPerFeet, [inchesPerFeet]);

  return (
    <div style={{ display: "flex", gap: 16, alignItems: "center", padding: "8px 12px", background: "#0b1324", color: "#e7eefc", borderRadius: 8, marginBottom: 10 }}>
      <strong>Calibration</strong>
      <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <input type="radio" checked={mode === "ratio"} onChange={() => setMode("ratio")} />
        <span>Ratio&nbsp;1″ =</span>
        <input
          type="number"
          value={inchesPerFeet}
          min={1}
          onChange={(e) => setInchesPerFeet(Math.max(1, Number(e.target.value)))}
          style={{ width: 70 }}
        />
        <span>ft → <code>{computedPPF.toFixed(3)} pt/ft</code></span>
        <button
          onClick={() => {
            setPPF(computedPPF);
            savePPF(file, page, computedPPF);
          }}
          style={{ marginLeft: 8 }}
        >
          Use
        </button>
      </label>

      <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <input type="radio" checked={mode === "direct"} onChange={() => setMode("direct")} />
        <span>Direct&nbsp;ppf:</span>
        <input
          value={ppfDirect}
          onChange={(e) => setPpfDirect(e.target.value)}
          placeholder="points_per_foot"
          style={{ width: 120 }}
        />
        <button
          onClick={() => {
            const v = Number(ppfDirect);
            if (isFinite(v) && v > 0) {
              setPPF(v);
              savePPF(file, page, v);
            } else {
              alert("Enter a positive number");
            }
          }}
        >
          Save
        </button>
      </label>

      <div style={{ marginLeft: "auto" }}>
        <span>Active:&nbsp;</span>
        <strong>
          {ppf && isFinite(ppf) ? `${(72 / ppf).toFixed(1)}′ per 1″  (${ppf.toFixed(3)} pt/ft)` : "Not set"}
        </strong>
      </div>
    </div>
  );
}

// ----- Counts Table -----
function CountsTable({
  rows,
  ppf,
  onEdit,
  onJump,
  loading,
}: {
  rows: CountItem[];
  ppf: number;
  onEdit: (id: string, patch: Partial<CountItem>) => void;
  onJump: (row: CountItem) => void;
  loading?: boolean;
}) {
  const [minConf, setMinConf] = useState<number>(0);
  const [typeFilter, setTypeFilter] = useState<string>("");

  const filtered = rows.filter((r) => r.confidence >= minConf && (!typeFilter || r.type === typeFilter));
  const types = useMemo(() => Array.from(new Set(rows.map((r) => r.type))).sort(), [rows]);

  return (
    <div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "6px 0 10px" }}>
        <label>Min Confidence: <input type="number" min={0} max={1} step={0.05} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} style={{ width: 70 }} /></label>
        <label>Type:
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} style={{ marginLeft: 6 }}>
            <option value="">All</option>
            {types.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        {loading ? <span>Loading…</span> : null}
      </div>

      <div style={{ maxHeight: 360, overflow: "auto", border: "1px solid #e5e7eb", borderRadius: 8 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead style={{ position: "sticky", top: 0, background: "#f3f4f6" }}>
            <tr>
              <th style={th}>Status</th>
              <th style={th}>Type</th>
              <th style={th}>Conf</th>
              <th style={th}>Page</th>
              <th style={th}>X (ft)</th>
              <th style={th}>Y (ft)</th>
              <th style={th}>Note</th>
              <th style={th}>Jump</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const xft = r.x_pdf / ppf;
              const yft = r.y_pdf / ppf;
              return (
                <tr key={r.id}>
                  <td style={td}>
                    <select
                      value={r.status}
                      onChange={(e) => onEdit(r.id, { status: e.target.value as CountItem["status"] })}
                    >
                      <option>pending</option>
                      <option>accepted</option>
                      <option>rejected</option>
                      <option>edited</option>
                    </select>
                  </td>
                  <td style={td}>
                    <input
                      value={r.type_edited ?? r.type}
                      onChange={(e) => onEdit(r.id, { type_edited: e.target.value, status: "edited" })}
                      style={{ width: 110 }}
                    />
                  </td>
                  <td style={td} title={String(r.confidence)}>{fmtPct(r.confidence)}</td>
                  <td style={td} align="center">{r.page}</td>
                  <td style={td}>{fmtNum(xft)}</td>
                  <td style={td}>{fmtNum(yft)}</td>
                  <td style={td}>
                    <input
                      value={r.reviewer_note ?? ""}
                      onChange={(e) => onEdit(r.id, { reviewer_note: e.target.value })}
                      placeholder="note…"
                      style={{ width: 180 }}
                    />
                  </td>
                  <td style={td}>
                    <button onClick={() => onJump(r)}>Go</button>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td style={td} colSpan={8} align="center">No rows (adjust filters or run detection)</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", borderBottom: "1px solid #e5e7eb", fontWeight: 600 };
const td: React.CSSProperties = { padding: "6px 10px", borderBottom: "1px solid #f1f5f9" };

// ----- Main page -----
export default function PlanReview() {
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const [instance, setInstance] = useState<any>(null);

  const file = getParam("file", "280-utility-construction-plans.pdf");
  const page = Number(getParam("page", "1"));
  const [ppf, setPPF] = useState<number>(() => loadPPF(file, page) || 1.44); // default 1"=50'
  const [rows, setRows] = useState<CountItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReportOut | null>(null);

  // Init WebViewer
  useEffect(() => {
    if (!viewerRef.current) return;
    
    // Ensure the container has proper styling
    const container = viewerRef.current;
    container.style.position = 'relative';
    container.style.overflow = 'hidden';
    container.style.isolation = 'isolate';
    
    WebViewer(
      {
        path: "/lib",
        initialDoc: `${API}/files/${encodeURIComponent(file)}`,
        // licenseKey: import.meta.env.VITE_APRYSE_KEY,
        enableRedaction: false,
        enableMeasurement: false,
        enableFilePicker: false,
        enableFullAPI: true,
        css: `
          .DocumentContainer {
            position: relative !important;
            overflow: hidden !important;
            width: 100% !important;
            height: 100% !important;
            max-width: 100% !important;
            max-height: 100% !important;
          }
          .DocumentContainer > div {
            position: relative !important;
            overflow: hidden !important;
            width: 100% !important;
            height: 100% !important;
            max-width: 100% !important;
            max-height: 100% !important;
          }
          .DocumentContainer .DocumentViewer {
            position: relative !important;
            overflow: hidden !important;
            width: 100% !important;
            height: 100% !important;
          }
        `
      },
      viewerRef.current
    ).then((inst) => {
      setInstance(inst);
      inst.Core.documentViewer.addEventListener("documentLoaded", () => {
        inst.Core.documentViewer.setCurrentPage(page);
      });
    });
  }, [file, page]);

  // Actions
  async function runDetection() {
    if (!isFinite(ppf) || ppf <= 0) {
      alert("Set calibration (points_per_foot) first");
      return;
    }
    setLoading(true);
    try {
      await fetch(`${API}/v1/detect?file=${encodeURIComponent(file)}&page=${page}&points_per_foot=${ppf}`, { method: "POST" });
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function refresh() {
    const res = await fetch(`${API}/v1/counts?file=${encodeURIComponent(file)}&page=${page}`);
    const data = await res.json();
    setRows(data);
  }

  async function commit() {
    const body = { file, pages: [page], threshold: 0.8 };
    const res = await fetch(`${API}/v1/review/commit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const rpt = await res.json();
    setReport(rpt);
  }

  async function onEdit(id: string, patch: Partial<CountItem>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
    await fetch(`${API}/v1/counts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
  }

  function onJump(row: CountItem) {
    jumpTo(instance, row.page, row.x_pdf, row.y_pdf);
  }

  // Auto-load counts on first mount
  useEffect(() => { refresh(); }, [file, page]);

  return (
    <div>
      <Header />
      
      {/* Sticky top toolbar */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        background: '#fff',
        borderBottom: '1px solid #e5e7eb',
        padding: '8px 12px',
        display: 'flex',
        gap: 8
      }}>
        <button onClick={runDetection}>Run Detection</button>
        <button onClick={refresh}>Refresh</button>
        <button onClick={commit} style={{ marginLeft: 'auto' }}>Commit Review</button>
      </div>

      <div style={{ display: "flex", gap: 16, padding: 16, height: "calc(100vh - 60px)" }}>
        {/* LEFT (Viewer) */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0, maxWidth: "calc(100% - 436px)" }}>
          <CalibrationBanner file={file} page={page} ppf={ppf} setPPF={(v) => { setPPF(v); savePPF(file, page, v); }} />
          <div
            ref={viewerRef}
            style={{
              flex: 1,
              width: "100%",
              height: "100%",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              overflow: "hidden",
              position: "relative",
              zIndex: 1,
              contain: "layout style paint size",
              isolation: "isolate",
              maxWidth: "100%",
              maxHeight: "100%"
            }}
          />
        </div>

        {/* RIGHT (Table + Metrics) */}
        <div style={{
          width: "420px",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          position: "relative",
          zIndex: 2 // on top if there's any overlap
        }}>
          <div style={{ fontSize: 13, color: "#475569" }}>
            <div><strong>File:</strong> {file}</div>
            <div><strong>Page:</strong> {page}</div>
            <div><strong>PPF:</strong> {isFinite(ppf) ? ppf.toFixed(3) : "—"} (pt/ft)</div>
          </div>

          <CountsTable rows={rows} ppf={ppf} onEdit={onEdit} onJump={onJump} loading={loading} />

          <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10 }}>
            <strong>Metrics</strong>
            {report ? (
              <div style={{ marginTop: 6, fontSize: 14 }}>
                <div>Total: {report.n_total} • TP: {report.n_tp} • FP: {report.n_fp} • FN: {report.n_fn}</div>
                <div>Precision: {fmtPct(report.precision)} • Recall: {fmtPct(report.recall)} • F1: {fmtPct(report.f1)}</div>
                <div>Loc MAE: {fmtNum(report.loc_mae_ft)} ft • P95: {fmtNum(report.loc_p95_ft)} ft</div>
                {report.export_csv_url ? (
                  <div style={{ marginTop: 6 }}>
                    <a href={`${API}${report.export_csv_url}`} target="_blank">Download accepted.csv</a>
                  </div>
                ) : null}
              </div>
            ) : (
              <div style={{ marginTop: 6, fontSize: 14, color: "#64748b" }}>Commit a review to see metrics</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
