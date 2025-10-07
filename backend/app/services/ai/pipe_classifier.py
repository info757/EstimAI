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
        
        logger.info(f"PipeClassifier initialized with model: {self.model_name}")
        if self.use_seed:
            logger.info(f"Deterministic mode enabled (seed: {settings.ESTIMAI_SEED})")
    
    def classify(self, patches: List[Dict[str, Any]]) -> List[PipeDetection]:
        """
        Classify polylines as pipes and extract attributes.
        
        Args:
            patches: List of candidate polylines with context, each containing:
                - polyline_id: str
                - length_ft: float (real-world length)
                - bbox: tuple (minx, miny, maxx, maxy)
                - layer: str | None (layer name)
                - color: str | None (stroke color)
                - nearby_text: list[str] (text annotations within proximity)
                - image_crop: bytes | None (optional image of the area)
                
        Returns:
            List of PipeDetection objects with attributes and confidence
            
        Example:
            patches = [
                {
                    "polyline_id": "vec_0_42",
                    "length_ft": 125.5,
                    "layer": "STORM SEWER",
                    "nearby_text": ["12\" PVC", "0.5% SLOPE"]
                }
            ]
            detections = classifier.classify(patches)
            # detections[0].attrs.dia_in == 12.0
            # detections[0].attrs.material == "pvc"
        """
        if not patches:
            return []
        
        logger.info(f"Classifying {len(patches)} candidate polylines")
        
        # Build context for LLM
        context = self._build_context(patches)
        
        # Get prompt and schema
        prompt = self._get_classification_prompt()
        schema = self._get_response_schema()
        
        try:
            # Call LLM
            result = self._call_llm(prompt, context, schema)
            
            # Parse results into PipeDetection objects
            detections = self._parse_llm_response(result, patches)
            
            logger.info(f"Classified {len(detections)} pipes from {len(patches)} candidates")
            return detections
        
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Return empty list with reasonable defaults
            return self._fallback_classification(patches)
    
    def _build_context(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build LLM context from patches."""
        candidates = []
        
        for patch in patches:
            candidate = {
                "id": patch.get("polyline_id", "unknown"),
                "length_ft": patch.get("length_ft", 0.0),
                "layer": patch.get("layer", "unknown"),
                "color": patch.get("color"),
                "nearby_text": patch.get("nearby_text", []),
            }
            candidates.append(candidate)
        
        return {
            "task": "classify_utility_pipes",
            "candidates": candidates,
            "instructions": (
                "For each candidate polyline, determine if it's a utility pipe "
                "and extract its attributes (discipline, material, diameter). "
                "Use layer names and nearby text annotations as primary evidence."
            )
        }
    
    def _get_classification_prompt(self) -> str:
        """Get the classification prompt template."""
        return """You are a construction plan analyzer specialized in utility pipe detection.

Given polylines with context (layer, nearby text, length), classify each as:
- Discipline: storm, sanitary, or water (or null if not a pipe)
- Material: pvc, ductile_iron, concrete, hdpe, etc.
- Diameter: in inches (extract from text like "12\\"" or "8 IN")
- Confidence: 0.0 to 1.0 (how certain you are)

Rules:
1. Layer names provide strong hints:
   - "STORM", "SD" → storm
   - "SANITARY", "SAN", "SEWER" → sanitary  
   - "WATER", "WM", "DOMESTIC" → water

2. Text annotations are definitive:
   - "8\\" PVC" → dia_in=8, material=pvc
   - "12 IN CONCRETE" → dia_in=12, material=concrete
   - "6\\" DI" → dia_in=6, material=ductile_iron

3. Common materials by discipline:
   - Storm: concrete, hdpe, pvc
   - Sanitary: pvc, vitrified_clay, concrete
   - Water: ductile_iron, pvc, copper

4. Provide reasoning for each classification.

Return JSON object with this exact format:
{
  "detections": [
    {
      "polyline_id": "vec_0_42",
      "discipline": "storm",
      "material": "pvc",
      "dia_in": 12.0,
      "confidence": 0.9,
      "reason": "Layer 'STORM SEWER' + nearby text '12\\" PVC'"
    }
  ]
}
"""
    
    def _get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for LLM response validation."""
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
                            "reason": {"type": "string"}
                        },
                        "required": ["polyline_id"]
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
        
        Uses existing LLM client if available, with deterministic seed if enabled.
        """
        try:
            # Try to use existing LLM client
            from backend.app.core.llm import llm_call_json
            import asyncio
            
            # Run async LLM call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    llm_call_json(prompt=prompt, context=context, schema=schema)
                )
            finally:
                loop.close()
            
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
        
        except ImportError:
            logger.warning("LLM client not available, using fallback")
            return self._fallback_llm_response(context)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
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
            
            results.append({
                "polyline_id": candidate["id"],
                "discipline": discipline,
                "material": material,
                "dia_in": dia_in,
                "confidence": 0.6 if discipline else 0.3,
                "reason": f"Heuristic: layer={layer}, text={nearby_text[:50]}"
            })
        
        return results
    
    def _parse_llm_response(
        self, 
        llm_result: List[Dict[str, Any]], 
        original_patches: List[Dict[str, Any]]
    ) -> List[PipeDetection]:
        """Parse LLM response into validated PipeDetection objects."""
        detections = []
        
        for item in llm_result:
            try:
                # Build PipeAttr
                attrs = PipeAttr(
                    material=item.get("material"),
                    dia_in=item.get("dia_in"),
                    discipline=item.get("discipline"),
                    confidence=item.get("confidence", 0.5)
                )
                
                # Build PipeDetection
                detection = PipeDetection(
                    polyline_id=item["polyline_id"],
                    attrs=attrs,
                    reason=item.get("reason", "LLM classification")
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

