import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReviewTable from "../components/ReviewTable";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function Review() {
  const [params, setParams] = useSearchParams();
  const file = params.get("file") || "";
  const page = Number(params.get("page") || "1");
  const [isRunning, setIsRunning] = useState(false);

  console.log("Review component loaded", { file, page });

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
        // The ReviewTable will handle refreshing its own data
        console.log("Takeoff completed successfully");
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

  const handleCommit = (report: any) => {
    console.log("Review committed:", report);
  };

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Takeoff Review</h2>
      
      {/* File and Page Input */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">File:</label>
            <input 
              type="text" 
              value={file} 
              onChange={e => setFile(e.target.value)}
              placeholder="e.g., 280-utility-construction-plans.pdf"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Page:</label>
            <input 
              type="number" 
              value={page} 
              onChange={e => setPage(Number(e.target.value))}
              min="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button 
              onClick={runTakeoff} 
              disabled={isRunning || !file}
              className={`px-4 py-2 rounded-md text-white font-medium ${
                isRunning || !file 
                  ? "bg-gray-400 cursor-not-allowed" 
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {isRunning ? "Running..." : "Run Takeoff"}
            </button>
          </div>
        </div>
      </div>

      {/* Review Table */}
      <ReviewTable 
        file={file}
        page={page}
        onCommit={handleCommit}
      />
    </div>
  );
}
