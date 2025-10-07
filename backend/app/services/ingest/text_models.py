"""
Unified text extraction models.

Provides a single, consistent shape for text runs across all extraction backends
(PDFNet, PyMuPDF, etc.).
"""

from pydantic import BaseModel, Field


class TextRun(BaseModel):
    """
    A single text run extracted from a PDF with spatial information.
    
    All text extractors (PDFNet, PyMuPDF, etc.) must return List[TextRun].
    Coordinates are in world feet for consistency with polyline geometry.
    
    Attributes:
        text: The actual text content
        bbox: Bounding box (minx, miny, maxx, maxy) in FEET
        
    Examples:
        >>> TextRun(text="18\" RCP", bbox=(100.5, 200.3, 125.8, 210.1))
        >>> TextRun(text="Storm Drain", bbox=(50.0, 75.0, 90.0, 80.0))
    """
    text: str = Field(description="Text content")
    bbox: tuple[float, float, float, float] = Field(
        description="Bounding box (minx, miny, maxx, maxy) in world feet"
    )
    
    @property
    def x(self) -> float:
        """X coordinate (center of bbox) in feet."""
        return (self.bbox[0] + self.bbox[2]) / 2.0
    
    @property
    def y(self) -> float:
        """Y coordinate (center of bbox) in feet."""
        return (self.bbox[1] + self.bbox[3]) / 2.0
    
    @property
    def width_ft(self) -> float:
        """Width of bounding box in feet."""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height_ft(self) -> float:
        """Height of bounding box in feet."""
        return self.bbox[3] - self.bbox[1]
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"TextRun('{self.text[:20]}...', x={self.x:.1f}ft, y={self.y:.1f}ft)"
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"TextRun(text='{self.text[:30]}', bbox={tuple(round(x, 2) for x in self.bbox)})"


__all__ = ["TextRun"]

