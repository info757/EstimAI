import React, { useRef, useState } from "react";

export function ClickScale({ onSubmit }: { onSubmit: (ftPerUnit:number)=>void }) {
  const [pts, setPts] = useState<{x:number;y:number}[]>([]);
  const [knownFt, setKnownFt] = useState(100);
  const ref = useRef<HTMLDivElement>(null);

  const onClick = (e: React.MouseEvent) => {
    const rect = (e.target as HTMLDivElement).getBoundingClientRect();
   const x = e.clientX - rect.left; const y = e.clientY - rect.top;
    setPts(prev => (prev.length >= 2 ? [{x,y}] : [...prev, {x,y}]));
  };

  const onConfirm = () => {
    if (pts.length < 2) return;
    const dx = pts[1].x - pts[0].x, dy = pts[1].y - pts[0].y;
    const units = Math.hypot(dx, dy);
    if (units <= 0) return;
    onSubmit(knownFt / units);
  };

  return (
    <div>
      <p>Click two points spanning a known distance (default 100 ft), then confirm.</p>
      <label>Known feet: <input type="number" value={knownFt} onChange={e=>setKnownFt(parseFloat(e.target.value||"0"))} /></label>
      <div onClick={onClick} style={{width:600, height:200, border:"1px dashed #aaa", margin:"8px 0", position:"relative"}}>
        {pts.map((p,i)=>(<div key={i} style={{position:"absolute", left:p.x-3, top:p.y-3, width:6,height:6, background:"#333", borderRadius:3}}/>))}
      </div>
      <button onClick={onConfirm} disabled={pts.length<2}>Use This Scale</button>
    </div>
  );
}

