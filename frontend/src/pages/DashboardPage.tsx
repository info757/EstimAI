import { Link } from 'react-router-dom';
import config from '../config';

export default function DashboardPage() {
  return (
    <div className="grid gap-6">
      <div className="text-xl font-semibold">Dashboard</div>
      <p className="opacity-80">
        This is a placeholder for the project dashboard. In the future it will
        list projects, jobs, and recent bids.
      </p>
      
      {/* Demo Project Link */}
      {config.demo.public && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-lg font-medium text-blue-900 mb-2">
            🎭 Demo Mode Active
          </h3>
          <p className="text-blue-700 mb-3">
            Try out EstimAI with our demo project - no login required!
          </p>
          <Link
            to={`/projects/${config.demo.projectId}`}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Open Demo Project
          </Link>
        </div>
      )}
    </div>
  );
}
  