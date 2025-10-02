from app.domain.dto import PageVectors, VectorPath, TextToken
from typing import List, Tuple

# Adjust these imports to your installed binding:
# Common patterns:
#   from PDFNetPython3 import PDFDoc, ElementReader, Element, PDFNet
#   or:
#   from pdftron.PDF import PDFDoc, ElementReader, Element
#   from pdftron import PDFNet
try:
    from PDFNetPython3 import PDFDoc, ElementReader, Element, PDFNet
except ImportError:
    from pdftron.PDF import PDFDoc, ElementReader, Element
    from pdftron import PDFNet

def _init_pdfnet(license_key: str | None):
    # Initialize once per process (guard if needed)
    if license_key:
        try:
            PDFNet.Initialize(license_key)
        except Exception:
            pass

def _rgb_from_gstate(gs) -> Tuple[int,int,int] | None:
    try:
        c = gs.GetStrokeColorSpace()
        if c is None: return None
        # Convert to RGB (simplified)
        rgb = [int(min(1.0, max(0.0, v))*255) for v in gs.GetStrokeColor()]
        return (rgb[0], rgb[1], rgb[2]) if len(rgb) >= 3 else None
    except Exception:
        return None

class ApryseIngestor:
    def __init__(self, license_key: str | None = None):
        _init_pdfnet(license_key)

    def get_page_count(self, pdf_path: str) -> int:
        doc = PDFDoc(pdf_path)
        doc.InitSecurityHandler()
        return doc.GetPageCount()

    def read_page(self, pdf_path: str, page_index: int) -> PageVectors:
        doc = PDFDoc(pdf_path); doc.InitSecurityHandler()
        page = doc.GetPage(page_index + 1)
        w, h = float(page.GetPageWidth()), float(page.GetPageHeight())

        reader = ElementReader()
        paths: List[VectorPath] = []
        texts: List[TextToken] = []

        def walk_page(p):
            reader.Begin(p)
            self._walk(reader, paths, texts, page_index)
            reader.End()

        walk_page(page)
        return PageVectors(page_index=page_index, width_pt=w, height_pt=h, paths=paths, texts=texts)

    def _walk(self, reader, paths: List[VectorPath], texts: List[TextToken], page_index: int):
        elem = reader.Next()
        while elem is not None:
            t = elem.GetType()
            if t == Element.e_text:
                try:
                    gs = elem.GetGState()
                    bbox = elem.GetBBox()
                    s = elem.GetTextString()
                    # bbox.y1 is top, y2 is bottom; store lower-left origin like PDF points
                    texts.append(TextToken(
                        text=s.strip(),
                        x=float(bbox.x1),
                        y=float(bbox.y1),
                        width=float(bbox.x2 - bbox.x1),
                        height=float(bbox.y2 - bbox.y1),
                        rotation_deg=0.0,   # can inspect text matrix if needed
                        page_index=page_index
                    ))
                except Exception:
                    pass

            elif t in (Element.e_path, Element.e_rect, Element.e_oval):
                try:
                    gs = elem.GetGState()
                    if not gs or not gs.GetStroke():   # only keep stroked geometry for centerlines
                        pass
                    # Extract flattened path points in page coords
                    ctm = elem.GetCTM()  # current transform matrix
                    # Sample curve into polyline using path data iterator
                    pts: List[Tuple[float,float]] = []
                    it = elem.GetPathIterator()
                    last = (0.0, 0.0)
                    while not it.IsAtEnd():
                        typ = it.CurrentType()
                        if typ == Element.PathData.e_moveto:
                            x, y = it.CurrentPoint()
                            # apply CTM
                            X = ctm.mult_x(x, y); Y = ctm.mult_y(x, y)
                            pts.append((float(X), float(Y)))
                            last = (X, Y)
                        elif typ == Element.PathData.e_lineto:
                            x, y = it.CurrentPoint()
                            X = ctm.mult_x(x, y); Y = ctm.mult_y(x, y)
                            pts.append((float(X), float(Y)))
                            last = (X, Y)
                        elif typ == Element.PathData.e_cubicto:
                            # sample cubic curve with small step (MVP)
                            # you can refine with flattening tolerance later
                            p1 = last
                            x1,y1 = it.CurrentPoint()      # cp1
                            it.Next()
                            x2,y2 = it.CurrentPoint()      # cp2
                            it.Next()
                            x3,y3 = it.CurrentPoint()      # end
                            # simple 10-step sampling
                            for s in range(1, 11):
                                t = s/10.0
                                bx = (1-t)**3*p1[0] + 3*(1-t)**2*t*ctm.mult_x(x1,y1) + 3*(1-t)*t**2*ctm.mult_x(x2,y2) + t**3*ctm.mult_x(x3,y3)
                                by = (1-t)**3*p1[1] + 3*(1-t)**2*t*ctm.mult_y(x1,y1) + 3*(1-t)*t**2*ctm.mult_y(x2,y2) + t**3*ctm.mult_y(x3,y3)
                                pts.append((float(bx), float(by)))
                            last = (ctm.mult_x(x3,y3), ctm.mult_y(x3,y3))
                        it.Next()
                    if len(pts) >= 2:
                        color = _rgb_from_gstate(gs)
                        stroke_w = float(gs.GetLineWidth())
                        paths.append(VectorPath(
                            kind="polyline",
                            points=[(float(x), float(y)) for (x,y) in pts],
                            stroke_rgb=color,
                            stroke_width=stroke_w,
                            layer_hint=None,
                            page_index=page_index
                        ))
                except Exception:
                    pass

            elif t == Element.e_form:
                # recurse into XObject/form content
                reader.FormBegin()
                self._walk(reader, paths, texts, page_index)
                reader.End()

            elem = reader.Next()
