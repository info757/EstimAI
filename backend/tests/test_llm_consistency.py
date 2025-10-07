"""
LLM consistency harness - ensures deterministic behavior.

Runs the same input 10× and asserts identical output bytes.
If this fails with temperature=0 and seed set, something is non-deterministic:
- Upstream ordering issue
- Unstable IDs
- Float quantization issue
- Context length variation
"""
import json
import os
import pytest
from typing import Any, Dict, List


@pytest.fixture(autouse=True)
def setup_seed():
    """Ensure deterministic seed is set for all tests."""
    os.environ["ESTIMAI_SEED"] = "42"
    yield
    # Cleanup not needed - env persists for test session


@pytest.mark.consistency
def test_llm_output_consistency_10x():
    """
    Run the same canonicalized input 10× and assert identical outputs.
    
    This is the gold standard test for determinism:
    - Same input → same hash → same cache key
    - With seed=42, all 10 runs should be byte-identical
    
    If this fails, check:
    1. Is seed being used? (Check logs for "seed=42")
    2. Are inputs truly canonicalized? (Check content hash stability)
    3. Is cache working? (After first call, rest should be cache hits)
    """
    from backend.app.services.ai.pipe_classifier import PipeClassifier
    from backend.app.services.ai.canonicalize import content_hash
    
    # Create a realistic test input (simulating polylines from PDF)
    raw_patches = [
        {
            "polyline_id": "vec_0_42",  # This will be replaced with stable ID
            "length_ft": 125.5,
            "bbox": [100.0, 200.0, 300.0, 400.0],
            "layer": "STORM SEWER",
            "nearby_text": ["12\" PVC", "0.5% SLOPE"],
            "vertices": [[100.0, 200.0], [300.0, 400.0]]
        },
        {
            "polyline_id": "vec_0_43",
            "length_ft": 85.3,
            "bbox": [150.0, 250.0, 350.0, 450.0],
            "layer": "SANITARY",
            "nearby_text": ["8\" PVC"],
            "vertices": [[150.0, 250.0], [350.0, 450.0]]
        },
        {
            "polyline_id": "vec_0_44",
            "length_ft": 200.7,
            "bbox": [200.0, 300.0, 400.0, 500.0],
            "layer": "WATER",
            "nearby_text": ["6\" DI", "WATER MAIN"],
            "vertices": [[200.0, 300.0], [400.0, 500.0]]
        }
    ]
    
    # Initialize classifier
    classifier = PipeClassifier()
    
    # Run 10 times
    outputs = []
    hashes = []
    
    for i in range(10):
        # Classify (includes canonicalization)
        detections = classifier.classify(raw_patches)
        
        # Get content hash from classifier metadata
        hash_val = classifier.last_cache_metadata.get("content_hash")
        hashes.append(hash_val)
        
        # Convert to JSON-serializable format
        output = [
            {
                "polyline_id": d.polyline_id,
                "discipline": d.attrs.discipline,
                "material": d.attrs.material,
                "dia_in": d.attrs.dia_in,
                "confidence": d.attrs.confidence,
                "reason": d.reason
            }
            for d in detections
        ]
        
        outputs.append(output)
        
        print(f"Run {i+1}/10: {len(detections)} detections, hash={hash_val[:16] if hash_val else 'N/A'}")
    
    # Assert 1: All content hashes are identical
    assert len(set(hashes)) == 1, (
        f"Content hashes differ across runs! "
        f"This means canonicalization is non-deterministic. "
        f"Hashes: {set(hashes)}"
    )
    print(f"✅ Content hash stable: {hashes[0][:16]}")
    
    # Assert 2: All outputs are byte-identical
    outputs_json = [json.dumps(o, sort_keys=True) for o in outputs]
    first_output = outputs_json[0]
    
    for i, output in enumerate(outputs_json[1:], start=2):
        assert output == first_output, (
            f"Output {i} differs from output 1! "
            f"This means LLM is non-deterministic despite seed=42. "
            f"Diff length: {abs(len(output) - len(first_output))} bytes"
        )
    
    print(f"✅ All 10 outputs are byte-identical ({len(first_output)} bytes)")
    print(f"✅ Consistency test PASSED")


@pytest.mark.consistency
def test_canonicalization_idempotent():
    """
    Test that canonicalization is idempotent: canonicalize(canonicalize(x)) == canonicalize(x).
    """
    from backend.app.services.ai.canonicalize import canonicalize_bundle, content_hash
    
    raw_bundle = {
        "polylines": [
            {
                "id": "",  # Will be generated
                "vertices": [[100.123456, 200.654321], [300.987654, 400.123456]],
                "length_ft": 125.499999,  # Will be quantized
                "style": {
                    "width": 2.0000001,  # Will be quantized
                    "stroke_rgb": [255.0, 128.5, 0.0]  # Will be quantized
                },
                "nearest_labels": [
                    {"text": "12\" PVC", "dist_ft": 5.123456, "alongness": 0.999999}
                ]
            }
        ],
        "labels": [
            {"id": "label_2", "text": "PVC"},
            {"id": "label_1", "text": "STORM"}  # Will be sorted
        ],
        "nodes": []
    }
    
    # Canonicalize once
    canonical_1 = canonicalize_bundle(raw_bundle.copy())
    hash_1 = content_hash(canonical_1)
    
    # Canonicalize twice (should be identical)
    canonical_2 = canonicalize_bundle(canonical_1.copy())
    hash_2 = content_hash(canonical_2)
    
    assert hash_1 == hash_2, (
        f"Canonicalization is NOT idempotent! "
        f"Hash 1: {hash_1[:16]}, Hash 2: {hash_2[:16]}"
    )
    
    print(f"✅ Canonicalization is idempotent (hash: {hash_1[:16]})")


@pytest.mark.consistency
def test_content_hash_stable():
    """
    Test that identical content produces identical hashes.
    """
    from backend.app.services.ai.canonicalize import content_hash
    
    payload = {
        "candidates": [
            {"id": "P123abc", "length_ft": 125.5, "layer": "STORM", "bbox": [100.0, 200.0, 300.0, 400.0]}
        ],
        "legend_ontology": None,
        "scale_info": {"feet_per_point": None, "units": "feet"}
    }
    
    # Hash 10 times
    hashes = [content_hash(payload) for _ in range(10)]
    
    assert len(set(hashes)) == 1, (
        f"Content hashes are not stable! "
        f"Got {len(set(hashes))} different hashes"
    )
    
    print(f"✅ Content hash is stable: {hashes[0][:16]}")


@pytest.mark.consistency
def test_cache_hit_behavior():
    """
    Test that cache hits return identical results (no re-computation).
    """
    from backend.app.services.ai.pipe_classifier import PipeClassifier
    from backend.app.services.ai.llm_cache import get_cache_stats
    
    patches = [
        {
            "polyline_id": "vec_cache_test",
            "length_ft": 100.0,
            "bbox": [0.0, 0.0, 100.0, 100.0],
            "layer": "TEST",
            "nearby_text": ["TEST"],
            "vertices": [[0.0, 0.0], [100.0, 100.0]]
        }
    ]
    
    classifier = PipeClassifier()
    
    # First call (might be cache miss or hit)
    stats_before = get_cache_stats()
    result_1 = classifier.classify(patches)
    
    # Second call (should be cache hit)
    result_2 = classifier.classify(patches)
    stats_after = get_cache_stats()
    
    # Convert to JSON for comparison
    json_1 = json.dumps([
        {
            "polyline_id": d.polyline_id,
            "discipline": d.attrs.discipline,
            "material": d.attrs.material,
            "confidence": d.attrs.confidence
        }
        for d in result_1
    ], sort_keys=True)
    
    json_2 = json.dumps([
        {
            "polyline_id": d.polyline_id,
            "discipline": d.attrs.discipline,
            "material": d.attrs.material,
            "confidence": d.attrs.confidence
        }
        for d in result_2
    ], sort_keys=True)
    
    assert json_1 == json_2, "Cache hit produced different result!"
    
    print(f"✅ Cache hit behavior verified")
    print(f"   Cache entries: {stats_before['entry_count']} → {stats_after['entry_count']}")


@pytest.mark.consistency
@pytest.mark.slow
def test_consistency_across_batches():
    """
    Test that batching doesn't affect consistency.
    
    Classify 20 patches at once, then classify same 20 in 2 batches of 10.
    Results should be identical (order may differ, but content should match).
    """
    from backend.app.services.ai.pipe_classifier import PipeClassifier
    
    # Create 20 patches
    patches = [
        {
            "polyline_id": f"vec_batch_{i}",
            "length_ft": 100.0 + i,
            "bbox": [float(i), float(i), float(i+100), float(i+100)],
            "layer": "STORM" if i % 2 == 0 else "SANITARY",
            "nearby_text": [f"{8 + i % 5}\" PVC"],
            "vertices": [[float(i), float(i)], [float(i+100), float(i+100)]]
        }
        for i in range(20)
    ]
    
    classifier = PipeClassifier()
    
    # Classify all at once
    result_full = classifier.classify(patches)
    
    # Classify in batches (manually split to test batching logic)
    result_batch1 = classifier.classify(patches[:10])
    result_batch2 = classifier.classify(patches[10:])
    result_batched = result_batch1 + result_batch2
    
    # Sort both by ID for comparison
    full_sorted = sorted(result_full, key=lambda d: d.polyline_id)
    batched_sorted = sorted(result_batched, key=lambda d: d.polyline_id)
    
    # Compare
    assert len(full_sorted) == len(batched_sorted), (
        f"Different number of results: {len(full_sorted)} vs {len(batched_sorted)}"
    )
    
    for i, (d1, d2) in enumerate(zip(full_sorted, batched_sorted)):
        assert d1.polyline_id == d2.polyline_id, f"ID mismatch at position {i}"
        assert d1.attrs.discipline == d2.attrs.discipline, f"Discipline mismatch for {d1.polyline_id}"
        assert d1.attrs.material == d2.attrs.material, f"Material mismatch for {d1.polyline_id}"
        # Allow tiny confidence differences due to rounding
        if d1.attrs.confidence and d2.attrs.confidence:
            assert abs(d1.attrs.confidence - d2.attrs.confidence) < 0.01, (
                f"Confidence mismatch for {d1.polyline_id}: {d1.attrs.confidence} vs {d2.attrs.confidence}"
            )
    
    print(f"✅ Batching consistency verified ({len(patches)} patches)")


if __name__ == "__main__":
    # Run locally with: python -m pytest backend/tests/test_llm_consistency.py -v -m consistency
    pytest.main([__file__, "-v", "-m", "consistency"])

