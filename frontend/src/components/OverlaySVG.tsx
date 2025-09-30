import React from "react";

type Polyline = { polyline: number[][]; kind: "curb"|"sanitary"|"storm"|"water" };
type Polygon = { polygon: number[][]; kind: "pavement"|"building" };

const colorMap: Record<string,string> = {
  curb: "#111111",
  sanitary: "#cc0000",
  storm: "#0066ff",
  water: "#00aa66",
  pavement: "rgba(120,120,120,0.15)",
  building: "rgba(60,60,60,0.2)"
};

export function OverlaySVG({
  width,
  height,
  polylines,
  polygons
}: {
  width: number; height: number;
  polylines: Polyline[]; polygons: Polygon[];
}) {
  // Calculate bounds from all geometry
  const allPoints = [
    ...polygons.flatMap(p => p.polygon),
    ...polylines.flatMap(pl => pl.polyline)
  ];
  
  if (allPoints.length === 0) {
    return <svg width={width} height={height} style={{border:"1px solid #ddd"}}><text x={width/2} y={height/2} textAnchor="middle" fill="#999">No geometry to display</text></svg>;
  }
  
  const xs = allPoints.map(p => p[0]);
  const ys = allPoints.map(p => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  // Add 10% padding
  const padding = 0.1;
  const viewBox = `${minX - dataWidth * padding} ${minY - dataHeight * padding} ${dataWidth * (1 + 2*padding)} ${dataHeight * (1 + 2*padding)}`;
  
  return (
    <svg width={width} height={height} viewBox={viewBox} style={{border:"1px solid #ddd", background:"#fafafa"}}>
      {polygons.map((p, i) => (
        <polygon key={`pg-${i}`}
          points={p.polygon.map(([x,y])=>`${x},${y}`).join(" ")}
          fill={colorMap[p.kind]} stroke="#555" strokeWidth={1}/>
      ))}
      {polylines.map((pl, i) => (
        <polyline key={`pl-${i}`}
          points={pl.polyline.map(([x,y])=>`${x},${y}`).join(" ")}
          fill="none" stroke={colorMap[pl.kind]} strokeWidth={2}/>
      ))}
    </svg>
  );
}

