import React, { useState, useEffect } from 'react';
import { ingestAsync, getJob, getIngestManifest, rebuildIngestIndices } from '../api/client';
import type { JobStatus, IngestManifest, IngestItem } from '../types/api';


interface IngestSourcesProps {
  pid: string;
}

export function IngestSources({ pid }: IngestSourcesProps) {
  const [manifest, setManifest] = useState<IngestManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [rebuildJobId, setRebuildJobId] = useState<string | null>(null);

  const fetchManifest = async () => {
    try {
      setLoading(true);
      const data = await getIngestManifest(pid);
      setManifest(data);
    } catch (error) {
      console.error('Error fetching ingest manifest:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRebuildIndices = async () => {
    try {
      setRebuildLoading(true);
      const data = await rebuildIngestIndices(pid);
      setRebuildJobId(data.job_id);
      // Start polling for job completion
      pollRebuildJob(data.job_id);
    } catch (error) {
      console.error('Error starting rebuild:', error);
    } finally {
      setRebuildLoading(false);
    }
  };

  const pollRebuildJob = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        if (job.status === 'complete' || job.status === 'failed') {
          clearInterval(pollInterval);
          setRebuildJobId(null);
          if (job.status === 'complete') {
            // Refresh manifest after successful rebuild
            fetchManifest();
          }
        }
      } catch (error) {
        console.error('Error polling rebuild job:', error);
        clearInterval(pollInterval);
        setRebuildJobId(null);
      }
    }, 1500);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const truncateHash = (hash: string): string => {
    return hash.length > 8 ? `${hash.substring(0, 8)}...` : hash;
  };

  const getStatusBadge = (status: string, reason?: string) => {
    const baseClasses = "px-2 py-1 rounded-full text-xs font-medium";
    
    switch (status) {
      case 'indexed':
        return <span className={`${baseClasses} bg-green-100 text-green-800`}>Indexed</span>;
      case 'skipped':
        return <span className={`${baseClasses} bg-yellow-100 text-yellow-800`} title={reason}>Skipped</span>;
      case 'error':
        return <span className={`${baseClasses} bg-red-100 text-red-800`} title={reason}>Error</span>;
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>{status}</span>;
    }
  };

  useEffect(() => {
    fetchManifest();
  }, [pid]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Ingested Files</h3>
        <button
          onClick={handleRebuildIndices}
          disabled={rebuildLoading || rebuildJobId !== null}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {rebuildLoading ? 'Starting...' : rebuildJobId ? 'Rebuilding...' : 'Rebuild Indices'}
        </button>
      </div>

      {manifest?.items && manifest.items.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Indexed At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Content Hash
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {manifest.items.map((item, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.filename.toLowerCase().endsWith('.pdf') ? (
                      <a
                        href={`/api/projects/${pid}/view/${item.filename}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        {item.filename}
                      </a>
                    ) : (
                      item.filename
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatFileSize(item.size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.indexed_at ? formatDate(item.indexed_at) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(item.status, item.reason)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                    {truncateHash(item.content_hash)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className="capitalize">{item.source_type}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <p>No files have been ingested yet.</p>
          <p className="text-sm mt-1">Upload files using the panel above to get started.</p>
        </div>
      )}
    </div>
  );
}
