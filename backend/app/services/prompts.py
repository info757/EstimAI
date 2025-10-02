"""Prompt templates for LLM interactions."""
from typing import List, Tuple

# Edit these to match what you want to count
TYPES = ["water", "sewer", "storm", "structure"]

def prompt_takeoff(types: List[str]) -> Tuple[str, dict]:
    prompt = (
        "You are a construction takeoff assistant for civil/sitework plans.\n"
        "Given an image tile of a plan sheet, find ONLY these symbol types: "
        + ", ".join(types)
        + ". For each detection, output the center coordinates in pixel units of THIS image.\n"
        "If unsure, omit the detection. Return JSON ONLY.\n"
        "Coordinate system: x increases to the right, y increases downward. No explanations."
    )
    schema = {
        "type": "object",
        "properties": {
            "detections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": types},
                        "x_px": {"type": "number"},
                        "y_px": {"type": "number"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["type", "x_px", "y_px", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["detections"],
        "additionalProperties": False,
    }
    return prompt, schema
