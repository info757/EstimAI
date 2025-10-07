import { useState, useEffect } from 'react';

interface Polyline {
  id: string;
  length_ft: number;
  bbox: number[];
  layer: string;
  nearby_text: string[];
  legend_context: string[];
}

interface TextAnnotation {
  text: string;
  x: number;
  y: number;
}

interface PageData {
  page_num: number;
  scale: {
    scale_text: string;
    feet_per_inch: number;
    points_per_foot: number;
  } | null;
  legend_tokens: string[];
  polylines: Polyline[];
  polylines_total: number;
  text_annotations: TextAnnotation[];
  text_annotations_total: number;
  full_text_length: number;
}

interface DebugExtractResponse {
  file: string;
  pages: PageData[];
}

interface DebugCandidatesPanelProps {
  fileRef: string | null;
  onClose: () => void;
}

export default function DebugCandidatesPanel({ fileRef, onClose }: DebugCandidatesPanelProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DebugExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState(0);

  useEffect(() => {
    if (!fileRef) {
      setData(null);
      return;
    }

    const fetchDebugData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `/api/v1/debug/extract?file_ref=${encodeURIComponent(fileRef)}&max_pages=2&max_polylines=50`
        );
        
        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || `HTTP ${response.status}`);
        }
        
        const result: DebugExtractResponse = await response.json();
        setData(result);
      } catch (err) {
        setError(String(err));
        console.error('Debug extract failed:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDebugData();
  }, [fileRef]);

  const pageData = data?.pages?.[selectedPage];

  // Infer discipline from nearby_text and legend_context
  const inferDiscipline = (polyline: Polyline): { discipline: string | null; confidence: string } => {
    const allText = [...polyline.nearby_text, ...polyline.legend_context].join(' ').toLowerCase();
    
    // Check for storm indicators
    if (allText.match(/storm|stm|sd|rcp|culvert|cb/)) {
      return { discipline: 'storm', confidence: 'text-hint' };
    }
    
    // Check for sanitary indicators
    if (allText.match(/san|sanitary|sewer|ss|sdr-?35/)) {
      return { discipline: 'sanitary', confidence: 'text-hint' };
    }
    
    // Check for water indicators
    if (allText.match(/water|wat|wtr|c900|hydrant|di/)) {
      return { discipline: 'water', confidence: 'text-hint' };
    }
    
    // Check layer hint
    const layer = polyline.layer?.toLowerCase() || '';
    if (layer.match(/storm|stm|sd/)) {
      return { discipline: 'storm', confidence: 'layer-hint' };
    }
    if (layer.match(/san|ss|sewer/)) {
      return { discipline: 'sanitary', confidence: 'layer-hint' };
    }
    if (layer.match(/water|wat|wtr/)) {
      return { discipline: 'water', confidence: 'layer-hint' };
    }
    
    return { discipline: null, confidence: 'unknown' };
  };

  const getDisciplineColor = (discipline: string | null): string => {
    switch (discipline) {
      case 'storm': return 'text-blue-600 bg-blue-50';
      case 'sanitary': return 'text-green-600 bg-green-50';
      case 'water': return 'text-purple-600 bg-purple-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="fixed right-0 top-0 h-full w-[500px] bg-white shadow-2xl border-l border-gray-200 overflow-y-auto z-50">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex justify-between items-center">
        <div>
          <h2 className="font-semibold text-lg">🔍 Debug: Raw Candidates</h2>
          <p className="text-xs text-gray-500 mt-1">Extraction before LLM classification</p>
        </div>
        <button
          onClick={onClose}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          Close
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading && (
          <div className="text-center py-8 text-gray-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
            Loading extraction data...
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 text-sm text-red-700">
            <strong>Error:</strong> {error}
            <div className="mt-2 text-xs opacity-75">
              Make sure ESTIMAI_DEBUG=1 is set in backend environment.
            </div>
          </div>
        )}

        {data && !loading && (
          <>
            {/* Page selector */}
            {data.pages.length > 1 && (
              <div className="mb-4 flex gap-2">
                {data.pages.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedPage(idx)}
                    className={`px-3 py-1 text-sm rounded ${
                      selectedPage === idx
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    Page {idx}
                  </button>
                ))}
              </div>
            )}

            {pageData && (
              <>
                {/* Page info */}
                <div className="mb-4 space-y-2 text-sm">
                  <div className="bg-gray-50 rounded p-3">
                    <div className="font-medium text-gray-700 mb-1">Scale</div>
                    <div className="text-gray-600">
                      {pageData.scale?.scale_text || 'Not detected'}
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded p-3">
                    <div className="font-medium text-gray-700 mb-1">
                      Legend Tokens ({pageData.legend_tokens.length})
                    </div>
                    {pageData.legend_tokens.length > 0 ? (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {pageData.legend_tokens.slice(0, 5).map((token, i) => (
                          <span
                            key={i}
                            className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded"
                          >
                            {token}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-500 text-xs">No legend tokens found</div>
                    )}
                  </div>

                  <div className="bg-gray-50 rounded p-3">
                    <div className="font-medium text-gray-700 mb-1">Extraction Stats</div>
                    <div className="text-xs text-gray-600 space-y-1">
                      <div>Polylines: {pageData.polylines_total}</div>
                      <div>Text annotations: {pageData.text_annotations_total}</div>
                      <div>Full text length: {pageData.full_text_length} chars</div>
                    </div>
                  </div>
                </div>

                {/* Polylines list */}
                <div>
                  <h3 className="font-medium mb-2">
                    Polyline Candidates ({pageData.polylines.length})
                  </h3>

                  {pageData.polylines.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 text-sm">
                      No polylines extracted from this page.
                      <div className="mt-2 text-xs">
                        Check if PDF contains vector geometry.
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {pageData.polylines.map((polyline) => {
                        const { discipline, confidence } = inferDiscipline(polyline);
                        
                        return (
                          <div
                            key={polyline.id}
                            className="border border-gray-200 rounded p-3 text-sm hover:bg-gray-50"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="font-mono text-xs text-gray-500">
                                {polyline.id.slice(3, 11)}
                              </div>
                              <div className="text-right">
                                <div className="font-semibold text-gray-900">
                                  {polyline.length_ft.toFixed(1)} ft
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 mb-2">
                              <span
                                className={`text-xs px-2 py-1 rounded font-medium ${getDisciplineColor(
                                  discipline
                                )}`}
                              >
                                {discipline || 'unknown'}
                              </span>
                              <span className="text-xs text-gray-500">
                                ({confidence})
                              </span>
                            </div>

                            {polyline.layer && polyline.layer !== 'None' && (
                              <div className="text-xs text-gray-600 mb-1">
                                Layer: <span className="font-mono">{polyline.layer}</span>
                              </div>
                            )}

                            {polyline.nearby_text.length > 0 && (
                              <div className="mt-2 text-xs">
                                <div className="text-gray-500 mb-1">Nearby text (top 2):</div>
                                <div className="space-y-1">
                                  {polyline.nearby_text.slice(0, 2).map((text, i) => (
                                    <div
                                      key={i}
                                      className="bg-gray-50 px-2 py-1 rounded font-mono text-xs text-gray-700"
                                    >
                                      "{text.slice(0, 40)}{text.length > 40 ? '...' : ''}"
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {polyline.legend_context.length > 0 && (
                              <div className="mt-2 text-xs">
                                <div className="text-gray-500 mb-1">Legend context:</div>
                                <div className="bg-yellow-50 px-2 py-1 rounded text-xs text-gray-700">
                                  {polyline.legend_context.slice(0, 2).join(', ')}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

