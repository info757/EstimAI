# backend/app/services/bid.py
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional




from ..core.paths import artifacts_root, project_dir, stage_dir
from .overrides import get_reviewed_or_base

# Use centralized paths helper - lazy initialization
def _get_artifact_dir():
    return artifacts_root()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _latest_file(dirpath: Path, suffix: str) -> Optional[Path]:
    if not dirpath.exists():
        return None
    files = sorted([p for p in dirpath.glob(f"*{suffix}") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _load_scope(pid: str) -> Dict[str, Any]:
    scope_dir = stage_dir(pid, "scope")
    jf = _latest_file(scope_dir, ".json")
    if jf:
        base_data = _read_json(jf)
        # Use reviewed version if available, otherwise base
        if "inclusions" in base_data and base_data["inclusions"]:
            reviewed_inclusions = get_reviewed_or_base(pid, "scope", base_data["inclusions"])
            base_data["inclusions"] = reviewed_inclusions
        return base_data
    return {"project_id": pid, "scopes": []}


def _load_estimate(pid: str) -> Dict[str, Any]:
    est_dir = stage_dir(pid, "estimate")
    jf = _latest_file(est_dir, ".json")
    if jf:
        base_data = _read_json(jf)
        
        # Check if the loaded data is a list (reviewed items) or dict (full estimate)
        if isinstance(base_data, list):
            # This is reviewed items, need to find the base estimate structure
            base_estimate_files = [f for f in est_dir.glob("*.json") if f.name != "reviewed.json"]
            if base_estimate_files:
                # Get the most recent non-reviewed file
                latest_base = sorted(base_estimate_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
                base_data = _read_json(latest_base)
            else:
                # No base estimate file, create minimal structure
                base_data = {
                    "project_id": pid,
                    "items": [],
                    "subtotal": 0.0,
                    "overhead_pct": 10.0,
                    "profit_pct": 5.0,
                    "total_bid": 0.0,
                }
        
        # Use reviewed version if available, otherwise base
        if "items" in base_data and base_data["items"]:
            reviewed_items = get_reviewed_or_base(pid, "estimate", base_data["items"])
            base_data["items"] = reviewed_items
            # Recalculate totals with reviewed items
            new_subtotal = sum(item.get('total', 0) for item in reviewed_items)
            overhead_pct = float(base_data.get("overhead_pct", 10.0))
            profit_pct = float(base_data.get("profit_pct", 5.0))
            base_data["subtotal"] = new_subtotal
            base_data["total_bid"] = new_subtotal * (1 + overhead_pct/100.0) * (1 + profit_pct/100.0)
        return base_data
    # Minimal empty shape
    return {
        "project_id": pid,
        "items": [],
        "subtotal": 0.0,
        "overhead_pct": 10.0,
        "profit_pct": 5.0,
        "total_bid": 0.0,
    }


def _load_risks(pid: str) -> Dict[str, Any]:
    risk_dir = stage_dir(pid, "risk")
    jf = _latest_file(risk_dir, ".json")
    if jf:
        return _read_json(jf)
    return {"project_id": pid, "risks": []}


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def build_bid_pdf(pid: str) -> str:
    """
    Build a submission-ready Bid PDF using latest Scope, Estimate, and Risk artifacts.
    Saves to artifacts/{pid}/bid/<timestamp>.pdf and returns the absolute path.
    """
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except ImportError as e:
        raise RuntimeError("Missing dependency 'reportlab'. Install with: pip install reportlab") from e
    
    proj_dir = project_dir(pid)

    scope = _load_scope(pid)
    estimate = _load_estimate(pid)
    risks = _load_risks(pid)

    out_dir = stage_dir(pid, "bid")
    ts = time.strftime("%Y%m%d-%H%M%S")
    pdf_path = (out_dir / f"{ts}.pdf").resolve()

    styles = getSampleStyleSheet()
    story: List[Any] = []

    # Cover
    story.append(Paragraph(f"Bid Proposal – Project {pid}", styles["Title"]))
    story.append(Paragraph(time.strftime("%B %d, %Y"), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Scope
    story.append(Paragraph("Scope of Work", styles["Heading2"]))
    scopes = scope.get("scopes") or scope.get("scope") or []
    if isinstance(scopes, list) and scopes:
        for s in scopes[:50]:  # cap long lists for MVP
            story.append(Paragraph(f"• {s}", styles["Normal"]))
    else:
        story.append(Paragraph("No scope details available.", styles["Italic"]))
    story.append(Spacer(1, 12))

    # Estimate Table
    story.append(Paragraph("Estimate Summary", styles["Heading2"]))
    items = estimate.get("items", []) or []
    data = [["Description", "Qty", "Unit", "Unit Cost", "Total"]]
    for it in items:
        desc = str(it.get("description", ""))
        qty = it.get("qty", 0)
        unit = it.get("unit", "")
        unit_cost = it.get("unit_cost", 0.0)
        total = it.get("total", (qty or 0) * (unit_cost or 0.0))
        data.append([desc, f"{qty}", unit, f"${unit_cost:,.2f}", f"${total:,.2f}"])

    if len(data) == 1:
        story.append(Paragraph("No estimate items available.", styles["Italic"]))
    else:
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(tbl)

    # Totals
    subtotal = float(estimate.get("subtotal", 0.0))
    overhead_pct = float(estimate.get("overhead_pct", 10.0))
    profit_pct = float(estimate.get("profit_pct", 5.0))
    total_bid = float(estimate.get("total_bid", subtotal * (1 + overhead_pct/100) * (1 + profit_pct/100)))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Subtotal: ${subtotal:,.2f}", styles["Normal"]))
    story.append(Paragraph(f"Overhead: {overhead_pct:.2f}%", styles["Normal"]))
    story.append(Paragraph(f"Profit: {profit_pct:.2f}%", styles["Normal"]))
    story.append(Paragraph(f"<b>Total Bid: ${total_bid:,.2f}</b>", styles["Heading3"]))
    story.append(Spacer(1, 12))

    # Risks
    story.append(Paragraph("Risks & Clarifications", styles["Heading2"]))
    rlist = risks.get("risks", [])
    if isinstance(rlist, list) and rlist:
        limit = min(len(rlist), 5)
        for r in rlist[:limit]:
            desc = r.get("description") or r.get("category") or "Risk"
            story.append(Paragraph(f"• {desc}", styles["Normal"]))
    else:
        story.append(Paragraph("No material risks identified.", styles["Italic"]))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER)
    doc.build(story)

    return str(pdf_path)

