import { useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function Header() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  // Pull file/page from query (or set your own defaults)
  const file = params.get("file") || "280-utility-construction-plans.pdf";
  const page = Number(params.get("page") || "1");

  // Calibration: read from localStorage (key we've been using)
  const ppfKey = (f: string, p: number) => `ppf:${f}:${p}`;
  const ppf = Number(localStorage.getItem(ppfKey(file, page)) || "1.44"); // 1"=50' default

  const onRunTakeoff = useCallback(async () => {
    if (!(ppf > 0)) {
      alert("Set calibration first (points_per_foot).");
      return;
    }

    // 1) Kick off detection
    const url = `${API}/v1/detect?file=${encodeURIComponent(file)}&page=${page}&points_per_foot=${ppf}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) {
      const msg = await res.text().catch(() => res.statusText);
      alert(`Detect failed: ${res.status} ${msg}`);
      return;
    }

    // 2) Navigate to HITL table page
    navigate(`/review?file=${encodeURIComponent(file)}&page=${page}`);
  }, [file, page, ppf, navigate]);

  return (
    <header className="header" style={{ 
      display: "flex", 
      justifyContent: "space-between", 
      alignItems: "center", 
      padding: "12px 16px", 
      borderBottom: "1px solid #e5e7eb",
      background: "#fff",
      position: "relative",
      zIndex: 1001
    }}>
      <div className="header-title">
        <h1 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>EstimAI</h1>
      </div>
      <div className="header-actions" style={{ display: "flex", gap: 8 }}>
        <button 
          onClick={() => {/* your existing Upload */}} 
          style={{
            padding: "8px 16px",
            border: "1px solid #d1d5db",
            borderRadius: "6px",
            background: "#fff",
            cursor: "pointer"
          }}
        >
          Upload
        </button>
        <button 
          onClick={onRunTakeoff}
          style={{
            padding: "8px 16px",
            border: "none",
            borderRadius: "6px",
            background: "#3b82f6",
            color: "#fff",
            cursor: "pointer",
            fontWeight: "500"
          }}
        >
          Run Takeoff
        </button>
      </div>
    </header>
  );
}
