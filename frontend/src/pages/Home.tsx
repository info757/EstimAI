import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div style={{ padding: 20, maxWidth: 800, margin: "0 auto" }}>
      <h1>EstimAI - Construction Takeoff Platform</h1>
      <p>AI-powered construction symbol detection and takeoff review.</p>
      
      <div style={{ marginTop: 30 }}>
        <h2>Quick Links</h2>
        <ul>
          <li>
            <Link to="/plan">Plan Review</Link> - PDF viewer with AI detection
          </li>
          <li>
            <Link to="/review">Review</Link> - Review and edit detected items
          </li>
        </ul>
      </div>
      
      <div style={{ marginTop: 30, padding: 20, backgroundColor: "#f8fafc", borderRadius: 8 }}>
        <h3>Getting Started</h3>
        <ol>
          <li>Upload a PDF file using the Plan Review page</li>
          <li>Run AI detection to find construction symbols</li>
          <li>Review and edit the results in the Review page</li>
          <li>Export your takeoff data</li>
        </ol>
      </div>
    </div>
  );
}
