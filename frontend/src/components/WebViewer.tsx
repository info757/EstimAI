import React, { useEffect, useRef, useState } from 'react';
import WebViewer from '@pdftron/webviewer';

interface WebViewerProps {
  initialDoc?: string;
  onDocumentLoaded?: (doc: any) => void;
  onAnnotationChanged?: (annotations: any[]) => void;
  onPageChanged?: (pageNumber: number) => void;
  onSVGOverlay?: (svg: string) => void;
  className?: string;
}

const WebViewerComponent: React.FC<WebViewerProps> = ({
  initialDoc,
  onDocumentLoaded,
  onAnnotationChanged,
  onPageChanged,
  onSVGOverlay,
  className = 'webviewer-container'
}) => {
  const viewer = useRef<HTMLDivElement>(null);
  const [webViewerInstance, setWebViewerInstance] = useState<any>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!viewer.current) return;

    const initializeWebViewer = async () => {
      try {
        const licenseKey = import.meta.env.VITE_APRYSE_KEY;
        const docUrl = initialDoc || import.meta.env.VITE_INITIAL_DOC;

        const instance = await WebViewer(
          {
            path: '/lib/webviewer',
            licenseKey,
            initialDoc: docUrl,
            enableRedaction: true,
            enableMeasurement: true,
            enableFilePicker: true,
            enableFullAPI: true,
            // Enable SVG overlay for HiL (Highlight in Line)
            enableSVGOverlay: true,
            // Custom CSS for overlay styling
            customCss: `
              .svg-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 10;
              }
              .svg-overlay svg {
                width: 100%;
                height: 100%;
              }
            `
          },
          viewer.current
        );

        setWebViewerInstance(instance);
        setIsLoaded(true);

        // Set up event listeners
        const { documentViewer, annotationManager, Annotations } = instance.Core;

        // Document loaded event
        documentViewer.addEventListener('documentLoaded', () => {
          const doc = documentViewer.getDocument();
          onDocumentLoaded?.(doc);
        });

        // Page changed event
        documentViewer.addEventListener('pageNumberChanged', (pageNumber: number) => {
          onPageChanged?.(pageNumber);
        });

        // Annotation changed events
        annotationManager.addEventListener('annotationChanged', (annotations: any[], action: string) => {
          onAnnotationChanged?.(annotations);
        });

        // SVG overlay hook for HiL functionality
        documentViewer.addEventListener('pageComplete', (pageNumber: number) => {
          // Get SVG overlay data for the current page
          const pageView = documentViewer.getPageView(pageNumber);
          if (pageView && onSVGOverlay) {
            // Extract SVG data from the page
            const svgElement = pageView.getSvgOverlay();
            if (svgElement) {
              const svgString = new XMLSerializer().serializeToString(svgElement);
              onSVGOverlay(svgString);
            }
          }
        });

        // Custom HiL (Highlight in Line) functionality
        const setupHiL = () => {
          // Add custom annotation type for line highlighting
          const HiLAnnotation = class extends Annotations.FreeTextAnnotation {
                constructor() {
                  super();
                  this.setContents('HiL');
                  this.setCustomData('hil', 'true');
                }
          };

          // Register the custom annotation type
          annotationManager.registerAnnotationType('hil', HiLAnnotation);
        };

        setupHiL();

      } catch (error) {
        console.error('Failed to initialize WebViewer:', error);
      }
    };

    initializeWebViewer();

    // Cleanup
    return () => {
      if (webViewerInstance) {
        webViewerInstance.UI.dispose();
      }
    };
  }, []);

  // Method to add SVG overlay programmatically
  const addSVGOverlay = (svgString: string, pageNumber?: number) => {
    if (!webViewerInstance) return;

    const { documentViewer } = webViewerInstance.Core;
    const targetPage = pageNumber || documentViewer.getCurrentPage();

    // Create SVG overlay element
    const overlayElement = document.createElement('div');
    overlayElement.className = 'svg-overlay';
    overlayElement.innerHTML = svgString;

    // Add to the page view
    const pageView = documentViewer.getPageView(targetPage);
    if (pageView) {
      const pageElement = pageView.getPageElement();
      if (pageElement) {
        pageElement.appendChild(overlayElement);
      }
    }
  };

  // Method to get current page SVG data
  const getCurrentPageSVG = () => {
    if (!webViewerInstance) return null;

    const { documentViewer } = webViewerInstance.Core;
    const currentPage = documentViewer.getCurrentPage();
    const pageView = documentViewer.getPageView(currentPage);
    
    if (pageView) {
      const svgElement = pageView.getSvgOverlay();
      if (svgElement) {
        return new XMLSerializer().serializeToString(svgElement);
      }
    }
    return null;
  };

  // Expose methods via ref (if needed)
  React.useImperativeHandle(viewer, () => ({
    addSVGOverlay,
    getCurrentPageSVG,
    getInstance: () => webViewerInstance
  }));

  return (
    <div className={className}>
      <div ref={viewer} style={{ height: '100vh', width: '100%' }} />
      {!isLoaded && (
        <div style={{ 
          position: 'absolute', 
          top: '50%', 
          left: '50%', 
          transform: 'translate(-50%, -50%)',
          fontSize: '18px',
          color: '#666'
        }}>
          Loading WebViewer...
        </div>
      )}
    </div>
  );
};

export default WebViewerComponent;
