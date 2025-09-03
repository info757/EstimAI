import React, { useState, useCallback, useRef, useEffect } from 'react';
import { ingestFiles } from '../api/client';
import { useToast } from '../context/ToastContext';

interface UploadPanelProps {
  pid: string;
  onComplete?: () => void;
  onUploadStateChange?: (isUploading: boolean) => void;
}

interface FileWithProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
}

const ACCEPTED_TYPES = '.pdf,.docx,.xlsx,.csv,.png,.jpg';

export const UploadPanel: React.FC<UploadPanelProps> = ({ pid, onComplete, onUploadStateChange }) => {
  const [selectedFiles, setSelectedFiles] = useState<FileWithProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Notify parent component of upload state changes
  useEffect(() => {
    onUploadStateChange?.(isUploading);
  }, [isUploading, onUploadStateChange]);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    
    const newFiles: FileWithProgress[] = Array.from(files).map(file => ({
      file,
      progress: 0,
      status: 'pending'
    }));
    
    setSelectedFiles(prev => [...prev, ...newFiles]);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedFiles([]);
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0 || isUploading) return;

    setIsUploading(true);
    
    try {
      // Simulate progress for each file
      const files = selectedFiles.map(f => f.file);
      
      // Update status to uploading
      setSelectedFiles(prev => prev.map(f => ({ ...f, status: 'uploading' as const })));
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setSelectedFiles(prev => prev.map(f => 
          f.status === 'uploading' 
            ? { ...f, progress: Math.min(f.progress + Math.random() * 20, 90) }
            : f
        ));
      }, 200);

      // Call the API
      const result = await ingestFiles(pid, files);
      
      clearInterval(progressInterval);
      
      // Mark all files as completed
      setSelectedFiles(prev => prev.map(f => ({ ...f, progress: 100, status: 'completed' as const })));
      
      // Show success message with link to artifacts
      toast(`Successfully ingested ${result.files_count} files`, { 
        type: 'success',
        link: `/projects/${pid}`,
        label: 'View artifacts'
      });
      
      // Clear selection and refresh immediately
      clearSelection();
      onComplete?.();
      
    } catch (error) {
      console.error('Upload failed:', error);
      
      // Mark all files as error
      setSelectedFiles(prev => prev.map(f => ({ ...f, status: 'error' as const })));
      
      // Extract status code from error message if available
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const statusMatch = errorMessage.match(/ingest failed: (\d+)/);
      const statusCode = statusMatch ? statusMatch[1] : 'unknown';
      
      toast(`Upload failed (${statusCode}): ${errorMessage}`, { type: 'error' });
    } finally {
      setIsUploading(false);
    }
  }, [selectedFiles, isUploading, pid, toast, onComplete, clearSelection]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = (status: FileWithProgress['status']) => {
    switch (status) {
      case 'pending': return 'text-gray-600';
      case 'uploading': return 'text-blue-600';
      case 'completed': return 'text-green-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: FileWithProgress['status']) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'uploading': return '📤';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '⏳';
    }
  };

  return (
    <div className="mb-6 p-4 border border-gray-300 rounded-lg bg-white">
      <h3 className="text-lg font-semibold mb-4">Upload Documents</h3>
      
      {/* Drag and Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="space-y-2">
          <div className="text-4xl">📁</div>
          <p className="text-lg font-medium text-gray-700">
            Drag and drop files here, or{' '}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-blue-600 hover:text-blue-800 underline"
            >
              browse files
            </button>
          </p>
          <p className="text-sm text-gray-500">
            Accepted formats: {ACCEPTED_TYPES}
          </p>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES}
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <h4 className="font-medium text-gray-700 mb-2">Selected Files ({selectedFiles.length})</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {selectedFiles.map((fileInfo, index) => (
              <div
                key={`${fileInfo.file.name}-${index}`}
                className="flex items-center justify-between p-2 bg-gray-50 rounded border"
              >
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <span className={getStatusColor(fileInfo.status)}>
                    {getStatusIcon(fileInfo.status)}
                  </span>
                  <span className="text-sm font-medium text-gray-700 truncate">
                    {fileInfo.file.name}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({formatFileSize(fileInfo.file.size)})
                  </span>
                </div>
                
                {fileInfo.status === 'uploading' && (
                  <div className="flex items-center space-x-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${fileInfo.progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-8">
                      {Math.round(fileInfo.progress)}%
                    </span>
                  </div>
                )}
                
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  disabled={isUploading}
                  className="ml-2 text-red-600 hover:text-red-800 disabled:opacity-50"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 flex space-x-2">
          <button
            type="button"
            onClick={handleUpload}
            disabled={isUploading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? 'Uploading...' : `Upload ${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}`}
          </button>
          
          <button
            type="button"
            onClick={clearSelection}
            disabled={isUploading}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
};
