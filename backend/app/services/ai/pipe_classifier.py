"""
LLM-based pipe classifier for identifying and attributing utility pipes.

This module uses LLM analysis (text-only or vision) to classify polylines
as pipes and extract their attributes (material, diameter, discipline).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class PipeAttr(BaseModel):
    """Attributes of a detected pipe."""
    
    material: str | None = Field(
        default=None,
        description="Pipe material (e.g., 'pvc', 'ductile_iron', 'concrete')"
    )
    dia_in: float | None = Field(
        default=None,
        description="Pipe diameter in inches"
    )
    discipline: Literal["storm", "sanitary", "water"] | None = Field(
        default=None,
        description="Utility discipline/network type"
    )
    confidence: float = Field(
        default=0.5,
        description="Classification confidence (0.0 to 1.0)"
    )
    
    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        """Ensure confidence is in valid range [0, 1]."""
        return max(0.0, min(1.0, v))


class PipeDetection(BaseModel):
    """A detected pipe with its attributes and reasoning."""
    
    polyline_id: str = Field(
        description="ID of the polyline this detection refers to"
    )
    attrs: PipeAttr = Field(
        description="Detected pipe attributes"
    )
    reason: str = Field(
        default="",
        description="Explanation for this classification"
    )


class PipeClassifier:
    """
    Classify polylines as pipes using LLM analysis.
    
    This classifier takes candidate polylines with context (nearby text,
    layer hints, visual features) and uses an LLM to determine:
    1. Is this polyline actually a pipe?
    2. What type of pipe (storm/sanitary/water)?
    3. What are its attributes (material, diameter)?
    
    The classifier uses a few-shot prompt with examples and can operate
    in text-only mode (using annotations) or vision mode (analyzing images).
    """
    
    def __init__(self, model_name: str | None = None):
        """
        Initialize pipe classifier.
        
        Args:
            model_name: LLM model to use (defaults to settings.VISION_MODEL)
        """
        from backend.app.core.config import settings
        
        self.model_name = model_name or settings.VISION_MODEL
        self.use_seed = settings.ESTIMAI_SEED is not None
        
        # Track cache metadata from last classification
        self.last_cache_metadata: Dict[str, Any] = {}
        
        logger.info(f"PipeClassifier initialized with model: {self.model_name}")
        if self.use_seed:
            logger.info(f"Deterministic mode enabled (seed: {settings.ESTIMAI_SEED})")
    
    def classify(self, patches: List[Dict[str, Any]]) -> List[PipeDetection]:
        """
        Classify polylines as pipes and extract attributes with automatic batching.
        
        For large datasets (>15 patches), automatically splits into batches to prevent
        LLM timeouts and improve reliability.
        
        Args:
            patches: List of candidate polylines with context
                
        Returns:
            List of PipeDetection objects with attributes and confidence
        """
        if not patches:
            return []
        
        # Automatic batching for reliability
        BATCH_SIZE = 15  # Sweet spot: fast enough, small enough to avoid timeouts
        
        if len(patches) <= BATCH_SIZE:
            # Small dataset, process all at once
            logger.info(f"Classifying {len(patches)} candidate polylines (single batch)")
            return self._classify_batch(patches)
        else:
            # Large dataset, use batching
            logger.info(f"Classifying {len(patches)} candidate polylines ({(len(patches) + BATCH_SIZE - 1) // BATCH_SIZE} batches of {BATCH_SIZE})")
            
            all_detections = []
            for i in range(0, len(patches), BATCH_SIZE):
                batch = patches[i:i+BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(patches) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} patches)")
                detections = self._classify_batch(batch)
                all_detections.extend(detections)
                logger.info(f"Batch {batch_num}/{total_batches} complete: {len(detections)} detections")
            
            logger.info(f"All batches complete: {len(all_detections)} total detections from {len(patches)} candidates")
            return all_detections
    
    def _classify_batch(self, patches: List[Dict[str, Any]]) -> List[PipeDetection]:
        """
        Classify a single batch of patches with automatic retry on improbable results.
        
        Includes token budgeting to prevent context overflow.
        """
        from backend.app.services.ai.validation import validate_classification_result, log_run_invariants
        from backend.app.services.ai.token_budget import tile_large_context, log_token_stats
        from backend.app.core.config import settings
        
        # Build context for LLM
        context = self._build_context(patches)
        
        # Get prompt
        prompt = self._get_classification_prompt()
        
        # Check if context needs tiling
        tiled_contexts = tile_large_context(prompt, context)
        
        if len(tiled_contexts) > 1:
            logger.info(f"Context tiled into {len(tiled_contexts)} chunks")
            
            # Process each tile and merge results
            all_detections = []
            for i, tile_context in enumerate(tiled_contexts):
                logger.info(f"Processing tile {i+1}/{len(tiled_contexts)}...")
                tile_detections = self._classify_tile(tile_context, prompt)
                all_detections.extend(tile_detections)
            
            logger.info(f"Merged {len(all_detections)} detections from {len(tiled_contexts)} tiles")
            return all_detections
        else:
            # Single context, process normally
            return self._classify_tile(context, prompt)
    
    def _classify_tile(self, context: Dict[str, Any], prompt: str) -> List[PipeDetection]:
        """
        Classify a single tile (or full context if no tiling needed).
        
        Includes validation and retry logic.
        """
        from backend.app.services.ai.validation import validate_classification_result, log_run_invariants
        from backend.app.services.ai.token_budget import log_token_stats
        from backend.app.core.config import settings
        
        # Extract metadata for validation
        candidate_count = len(context.get("candidates", []))
        legend_present = context.get("legend_ontology") is not None
        label_count = sum(len(c.get("nearby_text", [])) for c in context.get("candidates", []))
        
        # Get prompt and schema
        prompt = self._get_classification_prompt()
        schema = self._get_response_schema()
        
        # Log token stats
        log_token_stats(prompt, context)
        
        # Attempt 1: Initial classification
        try:
            result = self._call_llm(prompt, context, schema)
            # Note: patches are embedded in context["candidates"], pass context for reference
            detections = self._parse_llm_response(result, context.get("candidates", []))
            
            # Log run-time invariants
            log_run_invariants(
                candidate_count=candidate_count,
                label_count=label_count,
                legend_present=legend_present,
                model=self.model_name,
                temperature=0,
                seed=settings.ESTIMAI_SEED,
                token_budget_used=None,  # TODO: wire from LLM response
                content_hash=self.last_cache_metadata.get("content_hash"),
                detection_count=len(detections)
            )
            
            # Validate result
            validation = validate_classification_result(
                detections=detections,
                candidate_count=candidate_count,
                legend_present=legend_present,
                label_count=label_count
            )
            
            if validation.should_retry:
                logger.warning(f"🔄 Retry attempt 1/1: {validation.reason}")
                
                # Attempt 2: Retry with same parameters (deterministic)
                try:
                    result_retry = self._call_llm(prompt, context, schema)
                    detections_retry = self._parse_llm_response(result_retry, context.get("candidates", []))
                    
                    logger.info(f"🔄 Retry result: {len(detections_retry)} detections")
                    
                    # If retry produced better results, use them
                    if len(detections_retry) > len(detections):
                        logger.info(f"✅ Retry improved: {len(detections)} → {len(detections_retry)}")
                        detections = detections_retry
                    else:
                        # Still zero or low, flag for HITL
                        logger.warning(f"⚠️ QA_FLAG: {validation.reason} (persists after retry)")
                        # Add QA flag to first detection or create one
                        if detections:
                            if not hasattr(detections[0], 'qa_flags'):
                                detections[0].qa_flags = []
                            detections[0].qa_flags.append(validation.reason)
                
                except Exception as e_retry:
                    logger.error(f"Retry failed: {e_retry}")
                    # Continue with original result
            
            return detections
            
        except Exception as e:
            logger.error(f"Tile classification failed: {e}")
            return self._fallback_classification(context.get("candidates", []))
    
    def _build_context(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build canonicalized LLM context from patches.
        
        Uses production canonicalization to ensure deterministic hashing.
        """
        from backend.app.services.ai.canonicalize import sanitize_number, stable_poly_id
        
        candidates = []
        
        for patch in patches:
            # Extract vertices for stable ID generation
            bbox = patch.get("bbox", [0, 0, 0, 0])
            vertices = patch.get("vertices", [])
            
            # If no vertices, approximate from bbox
            if not vertices and bbox:
                vertices = [
                    [bbox[0], bbox[1]],  # bottom-left
                    [bbox[2], bbox[3]]   # top-right
                ]
            
            # Generate stable ID
            poly_id = patch.get("polyline_id", "")
            if not poly_id or len(poly_id) < 10:
                poly_id = stable_poly_id(vertices) if vertices else f"poly_{hash(str(bbox))}"
            
            # Canonicalize candidate
            candidate = {
                "id": poly_id,
                "length_ft": sanitize_number(patch.get("length_ft")),
                "layer": patch.get("layer") or None,  # Explicit null
                "color": patch.get("color") or None,
                "nearby_text": sorted(patch.get("nearby_text", [])),  # Stable sort
                "bbox": [sanitize_number(x) for x in bbox],
            }
            candidates.append(candidate)
        
        # Stable sort by ID
        candidates.sort(key=lambda c: c["id"])
        
        # Collect ALL unique text from all patches (for legend reading)
        all_text_set = set()
        for candidate in candidates:
            all_text_set.update(candidate.get("nearby_text", []))
        page_text_all = sorted(list(all_text_set))  # Stable sort for determinism
        
        # Build full context with metadata
        context = {
            "task": "classify_utility_pipes",
            "candidates": candidates,
            "page_text": page_text_all,  # ALL text on page (includes legend!)
            "legend_ontology": None,  # Explicit null if not provided
            "scale_info": {
                "feet_per_point": None,  # TODO: wire scale
                "units": "feet"
            },
            "instructions": (
                "Read the page_text to find the legend/notes that explain what symbols mean. "
                "Then classify each candidate polyline using layer names, nearby text, and legend definitions."
            )
        }
        
        return context
    
    def _get_classification_prompt(self) -> str:
        """Get the classification prompt template - LLM-first, no hardcoded assumptions."""
        return """You are an expert at reading civil engineering utility plans. Your task is to classify polylines as utility pipes.

TASK: For each polyline, determine:
- Discipline: "storm" (storm drain), "sanitary" (sanitary sewer), or "water" (water main)
- Material: pvc, ductile_iron, concrete, hdpe, copper, etc.
- Diameter: in inches (from text like "12\\"", "8 IN", "6 INCH")
- Confidence: 0.0 to 1.0 (how certain you are)

HOW TO CLASSIFY (use ALL available clues):

1. READ THE LEGEND/NOTES FIRST
   - Every drawing explains its symbols differently
   - Look for text like: "WATER MAIN (Blue) - WM, HYD, GV"
   - Or: "SS = Sanitary Sewer", "Storm Drain - CB, DI, FES"
   - The legend tells you what abbreviations, colors, or symbols mean

2. MATCH POLYLINES USING ANY CLUES:
   - Layer names (e.g., "C-UTIL-WATR", "STORM", "SANITARY SEWER")
   - Nearby text labels (e.g., "12\\" PVC", "HYD", "SSMH", "DI", "INV OUT=421.80'")
   - Legend definitions (if legend says "WM = Water Main", then "WM" labels indicate water)
   - Common abbreviations: WM/HYD/GV=water, SS/SSMH/INV=sanitary, SD/CB/DI/FES=storm

3. BE FLEXIBLE AND ADAPTIVE:
   - Every PDF uses different conventions
   - Some use layers, some use colors, some use text labels
   - Use WHATEVER clues are present in THIS specific drawing
   - Don't require specific formats - adapt to what you see
   - If coordinates don't align, use text context and legend as primary signals

4. EXAMPLES OF REASONING:
   - "Legend says 'WATER MAIN - WM, HYD', nearby text 'HYD' → water"
   - "Layer name 'C-UTIL-SSWR', nearby 'SSMH-1 INV OUT=421.80' → sanitary"
   - "Legend says 'Storm Drain - CB, DI', nearby 'DI' label → storm"
   - "No legend, but layer 'STORM SEWER' → storm"

CRITICAL RULES:
- Classify INDEPENDENTLY - don't assume equal distribution of types
- If you find ANY evidence (legend, layer, label), make a classification
- Only use null when there is truly ZERO evidence
- Keep "reason" concise (≤25 words) - cite the specific clue
- Include cited text in "evidence_refs" array

Return JSON object with this exact format:
{
  "detections": [
    {
      "polyline_id": "vec_0_42",
      "discipline": "storm",
      "material": "pvc",
      "dia_in": 12.0,
      "confidence": 0.85,
      "reason": "Legend: 'Storm Drain - CB, DI' + nearby 'DI' label",
      "evidence_refs": ["DI", "Storm Drain"]
    }
  ]
}
"""
    
    def _get_response_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for LLM response validation with anti-collapse guardrails.
        
        New requirements:
        - evidence_refs must be non-empty if discipline != null
        - reason must be ≤25 words
        """
        return {
            "type": "object",
            "properties": {
                "detections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "polyline_id": {"type": "string"},
                            "discipline": {
                                "type": ["string", "null"],
                                "enum": ["storm", "sanitary", "water", None]
                            },
                            "material": {"type": ["string", "null"]},
                            "dia_in": {"type": ["number", "null"]},
                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "reason": {
                                "type": "string",
                                "description": "Concise reasoning (≤25 words)"
                            },
                            "evidence_refs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of cited labels/text (required if discipline != null)"
                            }
                        },
                        "required": ["polyline_id", "reason"]
                    }
                }
            },
            "required": ["detections"]
        }
    
    def _call_llm(
        self, 
        prompt: str, 
        context: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Call LLM with classification request.
        
        Logs content hash for reproducibility tracking.
        Uses existing LLM client if available, with deterministic seed if enabled.
        """
        from backend.app.services.ai.canonicalize import content_hash
        
        # Create content hash for reproducibility
        from backend.app.services.ai.llm_cache import PROMPT_VERSION, SCHEMA_VERSION, get_cache_key
        
        hash_full = content_hash(context)
        hash_short = hash_full[:16]
        cache_key_full = get_cache_key("gpt-4o-mini", PROMPT_VERSION, SCHEMA_VERSION, hash_full)
        
        # Store metadata for agent response
        self.last_cache_metadata = {
            "content_hash": hash_full,
            "content_hash_short": hash_short,
            "cache_key": cache_key_full,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
        }
        
        logger.info(f"🔑 Content hash: {hash_short} ({len(context.get('candidates', []))} candidates)")
        
        try:
            # Try to use existing LLM client
            from backend.app.core.llm import llm_call_json
            import asyncio
            
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # There's already a loop running (FastAPI/uvicorn)
                # We need to run the async call in a thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        llm_call_json(prompt=prompt, context=context, schema=schema)
                    )
                    result = future.result(timeout=120)  # 120 second timeout (LLM can be slow for many candidates)
            except RuntimeError:
                # No loop running, safe to create one
                result = asyncio.run(llm_call_json(prompt=prompt, context=context, schema=schema))
            
            logger.info(f"✅ LLM response received for hash {hash_short}")
            
            # Update metadata with token usage (if available from response metadata)
            # This will be set by the LLM client
            
            # Result should be a dict with a list key, or directly a list
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "detections" in result:
                return result["detections"]
            elif isinstance(result, dict) and "items" in result:
                return result["items"]
            else:
                logger.warning(f"Unexpected LLM response format: {type(result)}")
                return []
        
        except ImportError as e:
            logger.warning(f"LLM client not available, using fallback: {e}")
            return self._fallback_llm_response(context)
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return self._fallback_llm_response(context)
    
    def _fallback_llm_response(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback response when LLM is unavailable."""
        candidates = context.get("candidates", [])
        results = []
        
        for candidate in candidates:
            # Simple heuristic-based classification
            layer = (candidate.get("layer") or "").upper()
            nearby_text = " ".join(candidate.get("nearby_text", [])).upper()
            
            # Determine discipline from layer/text
            discipline = None
            if "STORM" in layer or "SD" in layer or "STORM" in nearby_text:
                discipline = "storm"
            elif "SAN" in layer or "SEWER" in layer or "SANITARY" in nearby_text:
                discipline = "sanitary"
            elif "WATER" in layer or "WM" in layer or "WATER" in nearby_text:
                discipline = "water"
            
            # Extract diameter from text
            dia_in = None
            import re
            dia_match = re.search(r'(\d+)\s*(?:IN|INCH|")', nearby_text)
            if dia_match:
                dia_in = float(dia_match.group(1))
            
            # Extract material from text
            material = None
            if "PVC" in nearby_text:
                material = "pvc"
            elif "DI" in nearby_text or "DUCTILE" in nearby_text:
                material = "ductile_iron"
            elif "CONC" in nearby_text:
                material = "concrete"
            
            # Collect evidence refs
            evidence_refs = []
            if discipline:
                if layer:
                    evidence_refs.append(f"layer:{layer[:20]}")
                if nearby_text:
                    evidence_refs.append(nearby_text[:30])
            
            results.append({
                "polyline_id": candidate["id"],
                "discipline": discipline,
                "material": material,
                "dia_in": dia_in,
                "confidence": 0.6 if discipline else 0.3,
                "reason": f"Heuristic: layer={layer[:15]}, text={nearby_text[:20]}",
                "evidence_refs": evidence_refs
            })
        
        return results
    
    def _parse_llm_response(
        self, 
        llm_result: List[Dict[str, Any]], 
        original_patches: List[Dict[str, Any]]
    ) -> List[PipeDetection]:
        """
        Parse LLM response into validated PipeDetection objects.
        
        Enforces anti-collapse guardrails:
        - Truncates reason to 25 words
        - Warns if discipline != null but evidence_refs is empty
        """
        detections = []
        
        for item in llm_result:
            try:
                discipline = item.get("discipline")
                evidence_refs = item.get("evidence_refs", [])
                reason = item.get("reason", "LLM classification")
                
                # Guardrail 1: Truncate reason to ≤25 words
                reason_words = reason.split()
                if len(reason_words) > 25:
                    reason = " ".join(reason_words[:25]) + "..."
                    logger.debug(f"Truncated reason for {item['polyline_id']} (was {len(reason_words)} words)")
                
                # Guardrail 2: Warn if discipline set but no evidence cited
                if discipline and not evidence_refs:
                    logger.warning(
                        f"⚠️ Contract violation: {item['polyline_id']} has discipline={discipline} "
                        f"but evidence_refs is empty. Reason: {reason}"
                    )
                
                # Build PipeAttr
                attrs = PipeAttr(
                    material=item.get("material"),
                    dia_in=item.get("dia_in"),
                    discipline=discipline,
                    confidence=item.get("confidence", 0.5)
                )
                
                # Build PipeDetection
                detection = PipeDetection(
                    polyline_id=item["polyline_id"],
                    attrs=attrs,
                    reason=reason
                )
                
                detections.append(detection)
            
            except Exception as e:
                logger.warning(f"Failed to parse detection for {item.get('polyline_id')}: {e}")
                continue
        
        return detections
    
    def _fallback_classification(self, patches: List[Dict[str, Any]]) -> List[PipeDetection]:
        """Fallback classification when LLM fails."""
        detections = []
        
        for patch in patches:
            # Minimal detection with low confidence
            detection = PipeDetection(
                polyline_id=patch.get("polyline_id", "unknown"),
                attrs=PipeAttr(
                    material=None,
                    dia_in=None,
                    discipline=None,
                    confidence=0.1
                ),
                reason="Fallback: LLM unavailable"
            )
            detections.append(detection)
        
        return detections


def classify_pipes(
    patches: List[Dict[str, Any]], 
    model_name: str | None = None
) -> List[PipeDetection]:
    """
    Convenience function to classify pipes.
    
    Args:
        patches: List of polyline candidates with context
        model_name: Optional LLM model name
        
    Returns:
        List of PipeDetection objects
        
    Example:
        patches = [
            {
                "polyline_id": "vec_0_1",
                "length_ft": 125.5,
                "layer": "STORM SEWER",
                "nearby_text": ["12\\" PVC", "0.5% SLOPE"],
                "color": "#0000FF"
            }
        ]
        
        detections = classify_pipes(patches)
        for det in detections:
            if det.attrs.discipline == "storm":
                print(f"Storm pipe: {det.attrs.dia_in}\\" {det.attrs.material}")
    """
    classifier = PipeClassifier(model_name)
    return classifier.classify(patches)


# Prompt template for few-shot learning
FEW_SHOT_EXAMPLES = """
Example 1:
Input: {
  "polyline_id": "vec_0_15",
  "length_ft": 87.3,
  "layer": "C-STORM DRAIN",
  "nearby_text": ["SD-101", "12\\" RCP", "MH TO MH"]
}
Output: {
  "polyline_id": "vec_0_15",
  "discipline": "storm",
  "material": "concrete",
  "dia_in": 12.0,
  "confidence": 0.95,
  "reason": "Layer 'C-STORM DRAIN' clearly indicates storm network; '12\\" RCP' means 12-inch reinforced concrete pipe"
}

Example 2:
Input: {
  "polyline_id": "vec_0_23",
  "length_ft": 45.2,
  "layer": "P-WATER",
  "nearby_text": ["6\\" DI", "DOMESTIC WATER"]
}
Output: {
  "polyline_id": "vec_0_23",
  "discipline": "water",
  "material": "ductile_iron",
  "dia_in": 6.0,
  "confidence": 0.9,
  "reason": "Layer 'P-WATER' + text 'DOMESTIC WATER' confirms water line; '6\\" DI' is 6-inch ductile iron"
}

Example 3:
Input: {
  "polyline_id": "vec_0_31",
  "length_ft": 102.0,
  "layer": "SEWER",
  "nearby_text": ["8\\" PVC", "SANITARY", "MH-5 TO MH-6"]
}
Output: {
  "polyline_id": "vec_0_31",
  "discipline": "sanitary",
  "material": "pvc",
  "dia_in": 8.0,
  "confidence": 0.95,
  "reason": "Layer 'SEWER' + text 'SANITARY' indicates sanitary network; '8\\" PVC' specifies material and size"
}

Example 4 (non-pipe):
Input: {
  "polyline_id": "vec_0_50",
  "length_ft": 200.0,
  "layer": "PROPERTY LINE",
  "nearby_text": ["N 89°45'30\\" E"]
}
Output: {
  "polyline_id": "vec_0_50",
  "discipline": null,
  "material": null,
  "dia_in": null,
  "confidence": 0.1,
  "reason": "Layer 'PROPERTY LINE' and surveying notation indicate boundary, not utility pipe"
}
"""


def get_classification_prompt_with_examples() -> str:
    """Get full classification prompt with few-shot examples."""
    base_prompt = PipeClassifier(None)._get_classification_prompt()
    return f"{base_prompt}\n\n## Few-Shot Examples\n\n{FEW_SHOT_EXAMPLES}"

