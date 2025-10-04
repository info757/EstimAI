from __future__ import annotations
import hashlib, json
from typing import Iterable, Dict, Any, List, Optional
from backend.app.schemas_estimai import EstimAIResult, Pipe, Node
# import your actual CountItemCreate / repository / session interfaces:
# from backend.app.models.counts import CountItemCreate
# from backend.app.services.counts_repo import CountsRepo

def _src_key(sheet: Optional[str], geom_id: str, category: str) -> str:
    raw = json.dumps({"sheet": sheet or "", "geom_id": geom_id, "cat": category}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()  # idempotency key

def _pipe_to_count_items(
    pipes: Iterable[Pipe], category: str, sheet: Optional[str]
) -> List[Dict[str, Any]]:
    items = []
    for p in pipes:
        attrs = {
            "length_ft": round(p.length_ft, 3),
            "diameter_in": p.dia_in,
            "material": p.mat,
            "slope_frac": p.slope,
            "avg_depth_ft": p.avg_depth_ft,
            "from_id": p.from_id, "to_id": p.to_id,
        }
        
        # Add depth analysis fields from extra if available
        if hasattr(p, 'extra') and p.extra:
            extra = p.extra
            # Add depth statistics
            if "min_depth_ft" in extra:
                attrs["min_depth_ft"] = extra["min_depth_ft"]
            if "max_depth_ft" in extra:
                attrs["max_depth_ft"] = extra["max_depth_ft"]
            if "p95_depth_ft" in extra:
                attrs["p95_depth_ft"] = extra["p95_depth_ft"]
            
            # Add depth buckets
            buckets = extra.get("buckets_lf", {})
            if "0-5" in buckets:
                attrs["d_0_5"] = buckets["0-5"]
            if "5-8" in buckets:
                attrs["d_5_8"] = buckets["5-8"]
            if "8-12" in buckets:
                attrs["d_8_12"] = buckets["8-12"]
            if "12+" in buckets:
                attrs["d_12_plus"] = buckets["12+"]
            
            # Add trench and validation fields
            if "trench_volume_cy" in extra:
                attrs["trench_volume_cy"] = extra["trench_volume_cy"]
            if "cover_ok" in extra:
                attrs["cover_ok"] = extra["cover_ok"]
            if "deep_excavation" in extra:
                attrs["deep_excavation"] = extra["deep_excavation"]
        
        items.append({
            "category": category,            # e.g., "storm_pipe" | "sanitary_pipe" | "water_pipe"
            "subtype": p.mat or "unknown",
            "name": p.id,
            "quantity": p.length_ft,
            "unit": "LF",
            "attributes": attrs,
            "source_ref": {"sheet": sheet, "geom_id": p.id, "hash": _src_key(sheet, p.id, category)},
        })
    return items

def _nodes_to_count_items(
    nodes: Iterable[Node], category: str, unit: str, sheet: Optional[str]
) -> List[Dict[str, Any]]:
    items = []
    for n in nodes:
        items.append({
            "category": category,            # e.g., "inlet", "manhole", "hydrant", "valve"
            "subtype": n.kind,
            "name": n.id,
            "quantity": 1,
            "unit": unit,                    # "EA"
            "attributes": {"x": n.x, "y": n.y, **(n.attrs or {})},
            "source_ref": {"sheet": sheet, "geom_id": n.id, "hash": _src_key(sheet, n.id, category)},
        })
    return items

def estimai_to_count_items(payload: EstimAIResult, sheet: Optional[str]=None) -> List[Dict[str, Any]]:
    """
    Flatten EstimAIResult into a list of count-item dicts aligned with your /v1/counts schema.
    This does NOT write to DB; it just shapes data for your existing repo/service.
    """
    out: List[Dict[str, Any]] = []
    nets = payload.networks

    if "storm" in nets:
        out += _pipe_to_count_items(nets["storm"].pipes, "storm_pipe", sheet)
        out += _nodes_to_count_items(nets["storm"].structures, "inlet", "EA", sheet)

    if "sanitary" in nets:
        out += _pipe_to_count_items(nets["sanitary"].pipes, "sanitary_pipe", sheet)
        out += _nodes_to_count_items(nets["sanitary"].manholes, "manhole", "EA", sheet)

    if "water" in nets:
        out += _pipe_to_count_items(nets["water"].pipes, "water_pipe", sheet)
        out += _nodes_to_count_items(nets["water"].hydrants, "hydrant", "EA", sheet)
        out += _nodes_to_count_items(nets["water"].valves, "valve", "EA", sheet)

    # Roadway / E&SC "rollups" as separate count categories
    if payload.roadway.curb_lf:
        out.append({
            "category": "curb_and_gutter",
            "subtype": "LF_total",
            "name": "Curb & Gutter",
            "quantity": payload.roadway.curb_lf,
            "unit": "LF",
            "attributes": {},
            "source_ref": {"sheet": sheet, "geom_id": "CURB_TOTAL", "hash": _src_key(sheet,"CURB_TOTAL","curb_and_gutter")},
        })
    if payload.roadway.sidewalk_sf:
        out.append({
            "category": "sidewalk",
            "subtype": "SF_total",
            "name": "Sidewalk",
            "quantity": payload.roadway.sidewalk_sf,
            "unit": "SF",
            "attributes": {},
            "source_ref": {"sheet": sheet, "geom_id": "SIDEWALK_TOTAL", "hash": _src_key(sheet,"SIDEWALK_TOTAL","sidewalk")},
        })
    if payload.e_sc.silt_fence_lf:
        out.append({
            "category": "silt_fence",
            "subtype": "LF_total",
            "name": "Silt Fence",
            "quantity": payload.e_sc.silt_fence_lf,
            "unit": "LF",
            "attributes": {},
            "source_ref": {"sheet": sheet, "geom_id": "SILT_TOTAL", "hash": _src_key(sheet,"SILT_TOTAL","silt_fence")},
        })
    if payload.e_sc.inlet_protection_ea:
        out.append({
            "category": "inlet_protection",
            "subtype": "EA_total",
            "name": "Inlet Protection",
            "quantity": payload.e_sc.inlet_protection_ea,
            "unit": "EA",
            "attributes": {},
            "source_ref": {"sheet": sheet, "geom_id": "INLET_PROT_TOTAL", "hash": _src_key(sheet,"INLET_PROT_TOTAL","inlet_protection")},
        })
    # Earthwork totals (optional)
    if payload.earthwork.cut_cy is not None:
        out.append({"category":"earthwork_cut","subtype":"CY_total","name":"Cut","quantity":payload.earthwork.cut_cy,"unit":"CY","attributes":{"source":payload.earthwork.source},"source_ref":{"sheet":sheet,"geom_id":"CUT_TOTAL","hash":_src_key(sheet,"CUT_TOTAL","earthwork_cut")}})
    if payload.earthwork.fill_cy is not None:
        out.append({"category":"earthwork_fill","subtype":"CY_total","name":"Fill","quantity":payload.earthwork.fill_cy,"unit":"CY","attributes":{"source":payload.earthwork.source},"source_ref":{"sheet":sheet,"geom_id":"FILL_TOTAL","hash":_src_key(sheet,"FILL_TOTAL","earthwork_fill")}})

    return out

def upsert_counts(session_id: str, items: List[Dict[str, Any]], repo) -> Dict[str, int]:
    """
    Uses your existing repository/service to upsert by the idempotency key.
    We assume your counts table supports a unique constraint on (session_id, source_hash) or similar.
    """
    created = 0; updated = 0
    for item in items:
        source_hash = item["source_ref"]["hash"]
        # existing = repo.find_by_source_hash(session_id, source_hash)
        existing = repo.find_one(session_id=session_id, source_hash=source_hash)
        if existing:
            repo.update_existing(existing.id, item)
            updated += 1
        else:
            repo.create_new(session_id=session_id, **item)
            created += 1
    return {"created": created, "updated": updated}
