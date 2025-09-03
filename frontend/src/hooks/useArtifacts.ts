import { useState, useEffect } from 'react';
import { listArtifacts } from '../api/client';
import type { ArtifactItem } from '../types/api';

export function useArtifacts(pid: string) {
  const [items, setItems] = useState<ArtifactItem[]>([]);
  const [loading, setLoading] = useState(true);
  
  const refresh = async () => {
    setLoading(true);
    try {
      const res = await listArtifacts(pid);
      // Transform Record<string, string> to ArtifactItem[]
      const transformedItems: ArtifactItem[] = Object.entries(res.artifacts).map(([key, path]) => ({
        path,
        type: key,
        created_at: undefined
      }));
      setItems(transformedItems);
    } catch (error) {
      console.error('Failed to fetch artifacts:', error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => { 
    refresh(); 
  }, [pid]);
  
  return { items, loading, refresh };
}
