from pathlib import Path
import json, pdfplumber
from ..core.paths import artifacts_root, project_dir, stage_dir

def _artifact_dir() -> Path:
    return artifacts_root()


def write_spec_index(pid: str) -> Path:
    proj = project_dir(pid)
    docs = proj / "docs"
    chunks = []
    if docs.exists():
        for pdf in sorted(docs.glob("*.pdf")):
            with pdfplumber.open(str(pdf)) as book:
                for i, page in enumerate(book.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if text:
                        for j in range(0, len(text), 1200):
                            chunks.append({"file": str(pdf), "page_number": i, "text": text[j:j+1200]})
    idx = {"project_id": pid, "specs": chunks}
    path = proj / "spec_index.json"
    path.write_text(json.dumps(idx, indent=2))
    return path

