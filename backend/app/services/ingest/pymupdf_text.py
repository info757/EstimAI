"""
PyMuPDF (fitz) text extraction backend.

Fast path for text extraction using PyMuPDF's word-level API with phrase merging.
Returns TextRun objects with coordinates in world feet.
"""

import logging
from typing import Callable, List, Tuple
from .text_models import TextRun

logger = logging.getLogger(__name__)

# Document cache to avoid reopening the same PDF multiple times
_DOC_CACHE = {}


def get_doc(pdf_path: str):
    """
    Get or open a PyMuPDF document with caching.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        PyMuPDF Document object (cached)
    """
    import fitz  # PyMuPDF
    
    if pdf_path not in _DOC_CACHE:
        logger.debug(f"Opening PDF with PyMuPDF: {pdf_path}")
        _DOC_CACHE[pdf_path] = fitz.open(pdf_path)
    
    return _DOC_CACHE[pdf_path]


def clear_doc_cache():
    """Clear the document cache and close all open documents."""
    global _DOC_CACHE
    for doc in _DOC_CACHE.values():
        try:
            doc.close()
        except:
            pass
    _DOC_CACHE.clear()
    logger.debug("Cleared PyMuPDF document cache")


def _merge_words_to_phrases(words_data: List[tuple]) -> List[tuple]:
    """
    Merge words on the same line into phrases.
    
    Handles cases like: "12\"", "PVC", "SDR-35" → "12\" PVC SDR-35"
    
    Args:
        words_data: List of (x0, y0, x1, y1, word, block_no, line_no, word_no)
        
    Returns:
        List of (x0, y0, x1, y1, phrase, block_no, line_no, word_no) with merged text
    """
    if not words_data:
        return []
    
    phrases = []
    current_phrase = None
    
    for word_data in words_data:
        x0, y0, x1, y1, word = word_data[0], word_data[1], word_data[2], word_data[3], word_data[4]
        block_no = word_data[5] if len(word_data) > 5 else 0
        line_no = word_data[6] if len(word_data) > 6 else 0
        word_no = word_data[7] if len(word_data) > 7 else 0
        
        if not word or not word.strip():
            continue
        
        # Start a new phrase or continue current one
        if current_phrase is None:
            # First word
            current_phrase = {
                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'text': word,
                'block': block_no, 'line': line_no,
                'words': [word]
            }
        else:
            # Check if same line (within 2pt vertical tolerance)
            same_line = (abs(y0 - current_phrase['y0']) < 2.0 and 
                        block_no == current_phrase['block'] and
                        line_no == current_phrase['line'])
            
            # Check if horizontally close (within 20pt)
            horizontal_gap = x0 - current_phrase['x1']
            close_enough = horizontal_gap < 20.0
            
            if same_line and close_enough:
                # Merge into current phrase
                current_phrase['text'] += ' ' + word
                current_phrase['x1'] = max(current_phrase['x1'], x1)
                current_phrase['y0'] = min(current_phrase['y0'], y0)
                current_phrase['y1'] = max(current_phrase['y1'], y1)
                current_phrase['words'].append(word)
            else:
                # Save current phrase and start new one
                phrases.append((
                    current_phrase['x0'], current_phrase['y0'],
                    current_phrase['x1'], current_phrase['y1'],
                    current_phrase['text'],
                    current_phrase['block'], current_phrase['line'], 0
                ))
                current_phrase = {
                    'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                    'text': word,
                    'block': block_no, 'line': line_no,
                    'words': [word]
                }
    
    # Add last phrase
    if current_phrase is not None:
        phrases.append((
            current_phrase['x0'], current_phrase['y0'],
            current_phrase['x1'], current_phrase['y1'],
            current_phrase['text'],
            current_phrase['block'], current_phrase['line'], 0
        ))
    
    logger.debug(f"Merged {len(words_data)} words into {len(phrases)} phrases")
    return phrases


def extract_text_runs_pymupdf(
    pdf_path: str,
    page_num: int,
    to_world_xy: Callable[[float, float], Tuple[float, float]]
) -> List[TextRun]:
    """
    Extract text runs from a PDF page using PyMuPDF with phrase merging.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page index (0-based)
        to_world_xy: Function to convert PDF points to world feet
        
    Returns:
        List of TextRun objects with coordinates in feet
        
    Notes:
        - PyMuPDF uses top-left origin, so Y coordinates are flipped
        - Merges words on same line into phrases (e.g., "12\" PVC SDR-35")
        - Fast and reliable with real bounding boxes
        - Uses document caching to avoid reopening
        
    Example:
        >>> def to_world(x, y): return (x * 0.208, y * 0.208)  # 1" = 15'
        >>> runs = extract_text_runs_pymupdf("plan.pdf", 0, to_world)
        >>> print(f"Extracted {len(runs)} text runs")
    """
    # Get cached document
    doc = get_doc(pdf_path)
    page = doc[page_num]
    
    # Get words with bounding boxes
    # Returns list of tuples: (x0, y0, x1, y1, word, block_no, line_no, word_no)
    words = page.get_text('words')
    
    # Merge words into phrases (line-aware)
    phrases = _merge_words_to_phrases(words)
    
    # Page height for Y-axis flipping
    H = page.rect.height
    
    runs = []
    for phrase_data in phrases:
        x0, y0, x1, y1, text = phrase_data[0], phrase_data[1], phrase_data[2], phrase_data[3], phrase_data[4]
        
        # Skip empty phrases
        if not text or not text.strip():
            continue
        
        # Flip Y coordinates (PyMuPDF origin is top-left, PDF is bottom-left)
        y0_flipped = H - y1  # Note: swap y0/y1 during flip
        y1_flipped = H - y0
        
        # Convert corners to world feet
        xw0, yw0 = to_world_xy(x0, y0_flipped)
        xw1, yw1 = to_world_xy(x1, y1_flipped)
        
        # Debug: log first few conversions
        if len(runs) < 3:
            logger.info(
                f"📐 Text '{text.strip()}': PDF points ({x0:.1f}, {y0_flipped:.1f}) "
                f"→ World feet ({xw0:.1f}, {yw0:.1f})"
            )
        
        # Create TextRun with normalized bbox (min/max ensures correct ordering)
        runs.append(TextRun(
            text=text.strip(),
            bbox=(
                min(xw0, xw1),  # minx
                min(yw0, yw1),  # miny
                max(xw0, xw1),  # maxx
                max(yw0, yw1)   # maxy
            )
        ))
    
    logger.info(f"Extracted {len(runs)} text runs from page {page_num} using PyMuPDF (phrases)")
    return runs


# Alias for compatibility
extract_text_runs_all_pymupdf = extract_text_runs_pymupdf


__all__ = ["extract_text_runs_pymupdf", "extract_text_runs_all_pymupdf", "get_doc", "clear_doc_cache"]

