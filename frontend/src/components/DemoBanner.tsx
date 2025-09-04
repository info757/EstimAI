import React from 'react';
import config from '../config';

export const DemoBanner: React.FC = () => {
  // Only show banner when demo mode is enabled
  if (!config.demo.public) {
    return null;
  }

  return (
    <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 text-center">
      <div className="max-w-5xl mx-auto flex items-center justify-center space-x-2 text-sm text-blue-700">
        <span className="text-blue-500">🎭</span>
        <span>You are viewing the public demo project. Uploads are rate-limited.</span>
      </div>
    </div>
  );
};

export default DemoBanner;
