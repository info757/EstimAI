// frontend/src/components/QAList.tsx
export function QAList({ qa }: { qa: {level:string;code:string;message:string;feature_id?:string}[] }) {
  if (!qa?.length) return null;
  return (
    <div className="absolute bottom-3 right-3 bg-white/90 text-sm p-3 rounded shadow max-w-sm max-h-48 overflow-auto">
      <div className="font-semibold mb-1">QA</div>
      {qa.map((q,i)=>(<div key={i} className={q.level==="error"?"text-red-600":"text-amber-600"}>
        {q.code}: {q.message}
      </div>))}
    </div>
  );
}
