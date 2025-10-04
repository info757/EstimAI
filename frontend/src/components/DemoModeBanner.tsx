import React, { useState, useEffect } from 'react';

interface DemoModeBannerProps {
  isVisible?: boolean;
  onClose?: () => void;
}

interface DemoBannerInfo {
  enabled: boolean;
  message: string;
  limits: {
    max_file_size: number;
    max_requests_per_minute: number;
    max_requests_per_hour: number;
    max_demo_sessions: number;
  };
  sample_files: string[];
}

export default function DemoModeBanner({ isVisible = true, onClose }: DemoModeBannerProps) {
  const [bannerInfo, setBannerInfo] = useState<DemoBannerInfo | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // Fetch demo mode information from backend
    const fetchDemoInfo = async () => {
      try {
        const response = await fetch('/v1/demo/banner');
        if (response.ok) {
          const data = await response.json();
          setBannerInfo(data);
        }
      } catch (error) {
        console.log('Demo mode info not available');
      }
    };

    fetchDemoInfo();
  }, []);

  // Don't show banner if demo mode is not enabled or if dismissed
  if (!bannerInfo?.enabled || isDismissed) {
    return null;
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    onClose?.();
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse"></div>
              <span className="font-semibold text-sm">DEMO MODE</span>
            </div>
            <span className="text-sm opacity-90">
              {bannerInfo.message}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm hover:bg-white/20 px-2 py-1 rounded transition-colors"
            >
              {isExpanded ? 'Less' : 'Details'}
            </button>
            <button
              onClick={handleDismiss}
              className="text-sm hover:bg-white/20 px-2 py-1 rounded transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-white/20">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div>
                <h4 className="font-semibold mb-2">File Limits</h4>
                <ul className="space-y-1 text-xs opacity-90">
                  <li>Max size: {formatFileSize(bannerInfo.limits.max_file_size)}</li>
                  <li>Formats: PDF only</li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Rate Limits</h4>
                <ul className="space-y-1 text-xs opacity-90">
                  <li>{bannerInfo.limits.max_requests_per_minute} requests/minute</li>
                  <li>{bannerInfo.limits.max_requests_per_hour} requests/hour</li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Sample Files</h4>
                <ul className="space-y-1 text-xs opacity-90">
                  {bannerInfo.sample_files.slice(0, 3).map((filename, index) => (
                    <li key={index} className="truncate">
                      {filename}
                    </li>
                  ))}
                  {bannerInfo.sample_files.length > 3 && (
                    <li className="text-xs opacity-75">
                      +{bannerInfo.sample_files.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Session Limits</h4>
                <ul className="space-y-1 text-xs opacity-90">
                  <li>Max sessions: {bannerInfo.limits.max_demo_sessions}</li>
                  <li>Auto-cleanup: 1 hour</li>
                </ul>
              </div>
            </div>
            
            <div className="mt-4 flex flex-wrap gap-2">
              <div className="bg-white/20 px-3 py-1 rounded-full text-xs">
                🚀 Perfect for demos
              </div>
              <div className="bg-white/20 px-3 py-1 rounded-full text-xs">
                🔒 Secure sandbox
              </div>
              <div className="bg-white/20 px-3 py-1 rounded-full text-xs">
                📊 Real-time metrics
              </div>
              <div className="bg-white/20 px-3 py-1 rounded-full text-xs">
                🎯 Production-ready
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Hook for using demo mode information
export function useDemoMode() {
  const [demoInfo, setDemoInfo] = useState<DemoBannerInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDemoInfo = async () => {
      try {
        const response = await fetch('/v1/demo/banner');
        if (response.ok) {
          const data = await response.json();
          setDemoInfo(data);
        }
      } catch (error) {
        console.log('Demo mode info not available');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDemoInfo();
  }, []);

  return {
    demoInfo,
    isLoading,
    isDemoMode: demoInfo?.enabled || false
  };
}
