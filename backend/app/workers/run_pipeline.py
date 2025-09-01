# backend/app/workers/run_pipeline.py
from __future__ import annotations

import time
from typing import Callable

from ..models.jobs import JobStatus
from ..services.jobs import update_job
from ..services.artifacts import collect_project_artifacts

# Import your existing orchestrator functions.
# These should already exist in your repo and be callable with (project_id: str).
from ..services import orchestrator


def _step(fn: Callable[[str], None], label: str, job_id: str, project_id: str, checkpoint: float) -> None:
    """Run a single pipeline step with progress/message updates."""
    update_job(job_id, status=JobStatus.running, message=f"Running {label}…", progress=max(0.0, checkpoint - 0.07))
    t0 = time.perf_counter()
    fn(project_id)  # execute the step
    dt = time.perf_counter() - t0
    # store per-step duration in meta (accumulate)
    job = update_job(job_id)  # load current
    meta = dict(job.meta)
    meta[f"{label}_sec"] = round(dt, 3)
    update_job(job_id, meta=meta, progress=checkpoint)


def run_pipeline(job_id: str, project_id: str) -> None:
    """
    Full pipeline:
      1) takeoff -> 2) scope -> 3) leveler -> 4) risk -> 5) estimate -> 6) bid_pdf
    Updates JobRecord throughout and attaches artifacts on success.
    """
    try:
        update_job(job_id, status=JobStatus.running, message="Starting pipeline…", progress=0.02)

        # Define steps (label, progress checkpoint, callable)
        steps = [
            ("takeoff", 0.18, getattr(orchestrator, "run_takeoff")),
            ("scope",   0.33, getattr(orchestrator, "run_scope")),
            ("leveler", 0.52, getattr(orchestrator, "run_leveler")),
            ("risk",    0.70, getattr(orchestrator, "run_risk")),
            ("estimate",0.86, getattr(orchestrator, "run_estimate")),
            ("bid_pdf", 1.00, getattr(orchestrator, "generate_bid_pdf")),
        ]

        for label, cp, fn in steps:
            _step(fn, label, job_id, project_id, cp)

        # Collect artifacts and mark complete
        arts = collect_project_artifacts(project_id)
        update_job(
            job_id,
            status=JobStatus.complete,
            progress=1.0,
            message="Pipeline complete",
            artifacts=arts,
        )

    except Exception as e:
        # Update job with failure info
        update_job(job_id, status=JobStatus.failed, message="Pipeline failed", error=str(e))
        # Re-raise so errors surface in logs
        raise
