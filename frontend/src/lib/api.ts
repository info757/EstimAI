// frontend/src/lib/api.ts
export type FeatureLine = { 
  id:string; 
  kind:string; 
  page_index:number; 
  points:[number,number][]; 
  dia_in?:number; 
  material?:string; 
  length_ft:number; 
  cover_ft_min?:number; 
  cover_ft_max?:number; 
  confidence:number; 
};

export type FeaturePoint = { 
  id:string; 
  kind:string; 
  page_index:number; 
  x:number; 
  y:number; 
  confidence:number; 
  note?:string 
};

export type TakeoffMVPOut = { 
  lines:FeatureLine[]; 
  points:FeaturePoint[]; 
  rollup:{
    linear_ft:Record<string,number>;
    counts:Record<string,number>;
    volumes_cy:Record<string,number>
  }; 
  qa:{
    level:string;
    code:string;
    message:string;
    feature_id?:string
  }[] 
};

export async function runTakeoffMVP(fileName:string, pageIndex:number, scale:number): Promise<TakeoffMVPOut> {
  const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const u = new URL(`${API}/v1/run/mvp`);
  u.searchParams.set('name', fileName);
  u.searchParams.set('page', String(pageIndex));
  u.searchParams.set('scale_in_equals_ft', String(scale));
  const r = await fetch(u); 
  if (!r.ok) throw new Error('mvp failed');
  return r.json();
}
