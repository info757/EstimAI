// frontend/src/components/Totals.tsx
import { TakeoffMVPOut } from '../lib/api';

export function Totals({ mvp }: { mvp?: TakeoffMVPOut }) {
  if (!mvp) return null;
  console.log('Totals component - MVP data:', mvp);
  const { linear_ft, counts, volumes_cy } = mvp.rollup;
  console.log('Totals component - counts:', counts);
  return (
    <div className="absolute top-3 right-3 bg-black/70 text-white text-sm p-3 rounded space-y-2">
      <div className="font-semibold">Linear Feet</div>
      {Object.entries(linear_ft).map(([k,v]) => <div key={k}>{k}: {v.toFixed(1)}</div>)}
      <div className="font-semibold pt-2">Counts</div>
      {Object.entries(counts).map(([k,v]) => <div key={k}>{k}: {v}</div>)}
      <div className="font-semibold pt-2">Volumes (CY)</div>
      {Object.entries(volumes_cy).map(([k,v]) => <div key={k}>{k}: {v.toFixed(1)}</div>)}
    </div>
  );
}
