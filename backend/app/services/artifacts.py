# backend/app/services/artifacts.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple


def project_root(project_id: str) -> Path:
    """
    Returns the canonical app-scoped project directory:
      backend/app/data/projects/{pid}
    """
    app_dir = Path(__file__).resolve().parents[1]
    return app_dir / "data" / "projects" / project_id


def _candidate_roots(project_id: str) -> Iterable[Tuple[str, Path]]:
    """
    Yield (prefix, project_dir) candidates to support both layouts:
      1) backend/app/data/projects/{pid}    → served at /projects/**
      2) backend/artifacts/{pid}            → served at /artifacts/**
      3) repo_root/artifacts/{pid}          → served at /artifacts/**
    The returned prefix is the URL segment used by your StaticFiles mount.
    """
    cur = Path(__file__).resolve()
    app_dir = cur.parents[1]           # backend/app
    backend_dir = cur.parents[2]       # backend
    repo_root = cur.parents[3]         # repo root

    # 1) App data/projects layout (mount at /projects)
    projects_base = app_dir / "data" / "projects"
    yield ("projects", projects_base / project_id)

    # 2) backend/artifacts layout (mount at /artifacts)
    yield ("artifacts", backend_dir / "artifacts" / project_id)

    # 3) repo_root/artifacts layout (mount at /artifacts)
    yield ("artifacts", repo_root / "artifacts" / project_id)


def _rel_from_base(prefix: str, base_dir: Path, file_path: Path) -> str:
    """
    Build a URL-relative path using the correct static prefix.
    Example: prefix='projects', base_dir=.../data/projects, file_path=.../data/projects/P1/artifacts/estimate.json
             -> 'projects/P1/artifacts/estimate.json'
    """
    return f"{prefix}/{file_path.relative_to(base_dir).as_posix()}"


def collect_project_artifacts(project_id: str) -> Dict[str, str]:
    """
    Gather available artifacts for a project, supporting both directory layouts.
    Returns a mapping: { logical_name: relative_static_path }

    Examples of returned entries:
      {
        "takeoff":      "projects/123/artifacts/takeoff.json",
        "scope":        "projects/123/artifacts/scope.json",
        "leveling":     "projects/123/artifacts/leveling.json",
        "risk":         "projects/123/artifacts/risk.json",
        "estimate":     "projects/123/artifacts/estimate.json",
        "sheet_index":  "projects/123/sheet_index.json",
        "spec_index":   "projects/123/spec_index.json",
        "bid_20250827": "projects/123/artifacts/bid/20250827-160244.pdf"
      }
    """
    out: Dict[str, str] = {}

    # Preferred keys to emit if files exist
    json_names = [
        "takeoff.json",
        "scope.json",
        "leveling.json",
        "risk.json",
        "estimate.json",
        "sheet_index.json",
        "spec_index.json",
    ]

    for prefix, project_dir in _candidate_roots(project_id):
        if not project_dir.exists():
            continue

        # Where JSON artifacts might live:
        # - app layout:   {project_dir}/artifacts/*.json
        # - alt layout:   sometimes directly under {project_dir}
        json_dirs = [
            project_dir / "artifacts",
            project_dir,  # fallback if files were written directly under the project dir
        ]

        for base in json_dirs:
            if not base.exists():
                continue
            for name in json_names:
                p = base / name
                if p.exists():
                    key = name.split(".", 1)[0]  # 'takeoff.json' -> 'takeoff'
                    out.setdefault(key, _rel_from_base(prefix, project_dir.parent, p))

        # Bid PDFs:
        # - app layout:   {project_dir}/artifacts/bid/*.pdf
        # - alt layout:   {project_dir}/bid/*.pdf
        bid_dirs = [
            project_dir / "artifacts" / "bid",
            project_dir / "bid",
        ]
        for bdir in bid_dirs:
            if not bdir.exists():
                continue
            for pdf in sorted(bdir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True):
                # Use a stable logical key; stem is usually timestamped already
                key = f"bid_{pdf.stem}"
                out.setdefault(key, _rel_from_base(prefix, project_dir.parent, pdf))

        # Optional docs (first PDF in docs/)
        docs_dir = project_dir / "docs"
        if docs_dir.exists():
            docs = sorted(docs_dir.glob("*.pdf"))
            if docs:
                out.setdefault("docs_sample_pdf", _rel_from_base(prefix, project_dir.parent, docs[0]))

        # If we found anything under this candidate, we can stop early.
        if out:
            break

    return out
