import { useEffect, useRef, useState } from 'react';
import WebViewer, { WebViewerInstance } from '@pdftron/webviewer';

type Props = {
  docUrl?: string;
  onInstance?: (instance: WebViewerInstance) => void;
  className?: string;
  Overlay?: React.ComponentType<any>;
  overlayProps?: any;
};

export default function PlanViewer({ docUrl, onInstance, className, Overlay, overlayProps }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<WebViewerInstance | null>(null);
  const [instance, setInstance] = useState<WebViewerInstance | null>(null);

  useEffect(() => {
    if (!containerRef.current || instanceRef.current) return;

    const loadWebViewer = async () => {
      try {
        const inst = await WebViewer({
          path: '/lib/webviewer',
          licenseKey: import.meta.env.VITE_APRYSE_KEY,
          initialDoc: docUrl || import.meta.env.VITE_INITIAL_DOC,
          fullAPI: true
        }, containerRef.current);
        
        instanceRef.current = inst;
        setInstance(inst);
        onInstance?.(inst);
        
        // Navigate to the target page after document loads
        inst.Core.documentViewer.addEventListener('documentLoaded', () => {
          const sp = new URLSearchParams(location.search);
          const targetPage = Math.max(1, Number(sp.get('page')) || 6);
          inst.Core.documentViewer.setCurrentPage(targetPage);
        });
      } catch (error) {
        console.error('Failed to load WebViewer:', error);
        // Retry after a short delay if the backend isn't ready
        if (docUrl && docUrl.includes('localhost:8000')) {
          setTimeout(() => {
            console.log('Retrying WebViewer load...');
            loadWebViewer();
          }, 2000);
        }
      }
    };

    loadWebViewer();
  }, [docUrl, onInstance]);

  return (
    <div className={className ?? 'w-full h-full relative'}>
      <div ref={containerRef} className="w-full h-full" />
      {instance && Overlay ? (
        <div className="pointer-events-none absolute inset-0">
          <Overlay instance={instance} {...overlayProps} />
        </div>
      ) : null}
    </div>
  );
}
