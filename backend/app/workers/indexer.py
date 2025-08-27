from pathlib import Path
import os, json, pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[3]
def _artifact_dir() -> Path:
    return Path(os.getenv("ARTIFACT_DIR", str(PROJECT_ROOT / "backend" / "artifacts")))


def index_pdf(pid: str, pdf_path: Path) -> dict:
    sheets = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            # very light title heuristic: first text line on page, if any
            text = (page.extract_text() or "").strip().splitlines()
            title = (text[0] if text else f"Page {i}")[:80]
            sheets.append({
                "sheet_id": f"A1.{i}",
                "file": str(pdf_path),
                "page_number": i,
                "discipline": "Architectural",
                "title": title,
            })
    return {"project_id": pid, "sheets": sheets}

def write_sheet_index(pid: str) -> Path:
    proj = _artifact_dir() / pid
    docs = proj / "docs"
    sheets_all = []
    if docs.exists():
        for pdf in sorted(docs.glob("*.pdf")):
            out = index_pdf(pid, pdf)
            sheets_all.extend(out["sheets"])
    if not sheets_all:
        sheets_all = [{"sheet_id": "A1.1", "file": "", "page_number": 1,
                       "discipline": "Architectural", "title": "Stub"}]
    idx = {"project_id": pid, "sheets": sheets_all}
    path = proj / "sheet_index.json"
    path.write_text(json.dumps(idx, indent=2))
    return path

