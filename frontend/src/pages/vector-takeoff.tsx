import React, { useState } from "react";
import { OverlaySVG } from "../components/OverlaySVG";
import { ClickScale } from "../components/ClickScale";

type TakeoffOK = {
  ok: true;
  page_index: number;
  quantities: {
    building_area_sf: number;
    pavement_area_sf: number;
    sidewalk_area_sf: number;
    curb_length_lf: number;
    sanitary_len_lf: number;
    storm_len_lf: number;
    water_len_lf: number;
    parking_stalls: number;
  };
  diagnostics: { ft_per_unit: number; scale_source: string; tolerances: any };
  overlays: {
    polylines: { polyline: number[][]; kind: "curb"|"sanitary"|"storm"|"water" }[];
    polygons: { polygon: number[][]; kind: "pavement"|"building" }[];
    points: { x:number; y:number; kind:string; depth_ft?:number }[];
  };
};

export default function VectorTakeoffPage() {
  const [file, setFile] = useState<File|null>(null);
  const [res, setRes] = useState<TakeoffOK|null>(null);
  const [error, setError] = useState<string| null>(null);
  const [loading, setLoading] = useState(false);

  const onUpload = async () => {
    if (!file) return;
    setLoading(true); setError(null); setRes(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("page_index", "1");
    try {
      const r = await fetch("/api/takeoff/vector?page_index=1", { method: "POST", body: fd });
      if (!r.ok) {
        const text = await r.text();
        setError(`HTTP ${r.status}: ${text || r.statusText}`);
        return;
      }
      const json = await r.json();
      if (!json.ok) { setError(`${json.code}: ${json.hint}`); }
      else { setRes(json); }
    } catch (e:any) {
      setError(e.message || "Upload failed");
    } finally { setLoading(false); }
  };

  const retryWithManualScale = async (ftPerUnit:number) => {
    if (!file) return;
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch(`/api/takeoff/vector?page_index=1&manual_ft_per_unit=${ftPerUnit}`, { method: "POST", body: fd });
      const json = await r.json();
      if (!json.ok) setError(`${json.code}: ${json.hint}`);
      else { setRes(json); setError(null); }
    } catch (e:any) {
      setError(e.message || "Upload failed");
    } finally { setLoading(false); }
  };

  return (
    <div style={{padding:20, maxWidth:1000, margin:"0 auto"}}>
      <h1>Vector Takeoff (beta)</h1>
      <input type="file" accept="application/pdf" onChange={e=>setFile(e.target.files?.[0]||null)} />
      <button onClick={onUpload} disabled={!file || loading} style={{marginLeft:10}}>
        {loading ? "Processing..." : "Run Takeoff"}
      </button>
      {error && (
        <div style={{color:"crimson", marginTop:12}}>
          Error: {error}
          {error.includes("SCALE_NOT_FOUND") && (
            <div style={{marginTop:12}}>
              <ClickScale onSubmit={retryWithManualScale}/>
            </div>
          )}
        </div>
      )}
      {res && (
        <div style={{marginTop:20}}>
          <h3>Quantities</h3>
          <ul>
            <li>Building: {res.quantities.building_area_sf.toFixed(1)} SF</li>
            <li>Pavement: {res.quantities.pavement_area_sf.toFixed(1)} SF</li>
            <li>Curb: {res.quantities.curb_length_lf.toFixed(1)} LF</li>
            <li>Sanitary: {res.quantities.sanitary_len_lf.toFixed(1)} LF</li>
            <li>Storm: {res.quantities.storm_len_lf.toFixed(1)} LF</li>
            <li>Water: {res.quantities.water_len_lf.toFixed(1)} LF</li>
          </ul>
          
          <h4>Overlays (page space preview)</h4>
          <OverlaySVG
            width={900}
            height={650}
            polylines={res.overlays.polylines}
            polygons={res.overlays.polygons}
          />
          
          <h4>Diagnostics</h4>
          <pre style={{background:"#f6f6f6", padding:12}}>{JSON.stringify(res.diagnostics, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

