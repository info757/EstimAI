"""
Spatial indexing for efficient text-to-geometry matching.

Provides a simple spatial index for finding text near polylines without
requiring external dependencies like rtree or shapely.
"""

import logging
from typing import List, Tuple
from backend.app.services.ingest.text_models import TextRun

logger = logging.getLogger(__name__)


class TextIndex:
    """
    Simple spatial index for text runs.
    
    Uses bounding box filtering and distance sorting for fast nearest-neighbor queries.
    Supports adaptive expansion when initial search yields too few results.
    
    Example:
        >>> index = TextIndex(text_runs)
        >>> nearby = index.query_expand(polyline_bbox, expand_ft=40, limit=20)
        >>> print(f"Found {len(nearby)} text runs near polyline")
    """
    
    def __init__(self, text_runs: List[TextRun]):
        """
        Initialize spatial index with text runs.
        
        Args:
            text_runs: List of TextRun objects to index
        """
        self.text_runs = text_runs
        logger.debug(f"Created TextIndex with {len(text_runs)} runs")
    
    def query_expand(
        self,
        bbox: Tuple[float, float, float, float],
        expand_ft: float = 40.0,
        limit: int = 20,
        adaptive: bool = True
    ) -> List[str]:
        """
        Query text runs near a bounding box with adaptive expansion.
        
        Args:
            bbox: Query bounding box (minx, miny, maxx, maxy) in feet
            expand_ft: Initial expansion distance in feet (default 40)
            limit: Maximum number of results to return (default 20)
            adaptive: If True and <8 hits, auto-expand to 80 ft
            
        Returns:
            List of text strings sorted by distance (closest first)
            
        Algorithm:
            1. Expand query bbox by expand_ft in all directions
            2. Filter text runs whose centers are in expanded bbox
            3. Calculate distance from bbox center to text center
            4. Sort by distance (ascending)
            5. If adaptive and <8 results, retry with 2x expansion
            6. Return top `limit` results
            
        Example:
            >>> bbox = (100, 200, 150, 250)  # Polyline bbox
            >>> nearby = index.query_expand(bbox, expand_ft=40, limit=10)
            >>> # Returns: ["18\" RCP", "Storm Drain", "MH-101", ...]
        """
        # Initial search
        results = self._query_bbox(bbox, expand_ft, limit)
        
        # Adaptive expansion if too few results
        if adaptive and len(results) < 8:
            logger.debug(f"Only {len(results)} results with expand_ft={expand_ft}, trying {expand_ft*2}")
            results = self._query_bbox(bbox, expand_ft * 2, limit)
        
        return results
    
    def _query_bbox(
        self,
        bbox: Tuple[float, float, float, float],
        expand_ft: float,
        limit: int
    ) -> List[str]:
        """
        Internal bbox query implementation.
        
        Args:
            bbox: Query bounding box (minx, miny, maxx, maxy) in feet
            expand_ft: Expansion distance in feet
            limit: Maximum results
            
        Returns:
            List of text strings sorted by distance
        """
        minx, miny, maxx, maxy = bbox
        
        # Expand query bbox
        query_bbox = (
            minx - expand_ft,
            miny - expand_ft,
            maxx + expand_ft,
            maxy + expand_ft
        )
        
        # Calculate bbox center for distance sorting
        center_x = (minx + maxx) / 2.0
        center_y = (miny + maxy) / 2.0
        
        # Filter text runs within expanded bbox and calculate distances
        candidates = []
        for run in self.text_runs:
            # Check if text center is within query bbox
            if (query_bbox[0] <= run.x <= query_bbox[2] and
                query_bbox[1] <= run.y <= query_bbox[3]):
                
                # Calculate Euclidean distance from bbox center to text center
                dx = run.x - center_x
                dy = run.y - center_y
                distance = (dx * dx + dy * dy) ** 0.5
                
                candidates.append((distance, run.text))
        
        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x[0])
        
        # Return text strings (drop distance)
        results = [text for dist, text in candidates[:limit]]
        
        logger.debug(f"Spatial query: bbox={bbox}, expand={expand_ft}ft → {len(results)} results")
        return results
    
    def query_point(
        self,
        x: float,
        y: float,
        radius_ft: float = 40.0,
        limit: int = 10
    ) -> List[str]:
        """
        Query text runs near a point.
        
        Args:
            x: X coordinate in feet
            y: Y coordinate in feet
            radius_ft: Search radius in feet (default 40)
            limit: Maximum results (default 10)
            
        Returns:
            List of text strings sorted by distance
            
        Example:
            >>> nearby = index.query_point(100.5, 200.3, radius_ft=30)
        """
        # Convert point to bbox
        bbox = (x - 0.1, y - 0.1, x + 0.1, y + 0.1)
        return self._query_bbox(bbox, radius_ft, limit)
    
    def get_stats(self) -> dict:
        """
        Get index statistics.
        
        Returns:
            Dict with: total_runs, total_chars, avg_chars_per_run
        """
        total_chars = sum(len(run.text) for run in self.text_runs)
        return {
            'total_runs': len(self.text_runs),
            'total_chars': total_chars,
            'avg_chars_per_run': total_chars / len(self.text_runs) if self.text_runs else 0
        }


__all__ = ["TextIndex"]

