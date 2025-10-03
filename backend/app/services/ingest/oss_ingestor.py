import fitz
from backend.app.domain.dto import PageVectors, VectorPath, TextToken

class OpenSourceIngestor:
    def get_page_count(self, pdf_path: str) -> int:
        with fitz.open(pdf_path) as doc:
            return len(doc)

    def read_page(self, pdf_path: str, page_index: int) -> PageVectors:
        doc = fitz.open(pdf_path); page = doc[page_index]
        w, h = float(page.rect.width), float(page.rect.height)

        texts = []
        for b in page.get_text("blocks"):
            x0,y0,x1,y1,txt,*_ = b
            if isinstance(txt, str) and txt.strip():
                texts.append(TextToken(text=txt.strip(), x=float(x0), y=float(y0),
                                       width=float(x1-x0), height=float(y1-y0),
                                       page_index=page_index))

        paths = []
        for d in page.get_drawings():
            color = d.get("color")
            width = float(d.get("linewidth", 1.0))
            poly = []
            for it in d["items"]:
                if it[0] == "l":
                    _, p1, p2 = it; poly += [(p1.x, p1.y), (p2.x, p2.y)]
                elif it[0] == "re":
                    # Handle rectangle items - they have different structure
                    if len(it) >= 2:
                        r = it[1]
                        poly += [(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1),(r.x0,r.y0)]
            if len(poly) >= 2:
                srgb = None if not color else (int(color[0]*255), int(color[1]*255), int(color[2]*255))
                paths.append(VectorPath(points=[(float(x),float(y)) for x,y in poly],
                                        stroke_rgb=srgb, stroke_width=width, page_index=page_index))
        doc.close()
        return PageVectors(page_index=page_index, width_pt=w, height_pt=h, paths=paths, texts=texts)
