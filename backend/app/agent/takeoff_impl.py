"""Default implementation of the TakeoffAgent protocol.

This adapter normalizes legacy call sites and provides a stable interface
between the new typed contract and the existing implementation. It handles:

1. **Legacy Function Adaptation**: Maps new typed requests to existing function signatures
2. **Error Handling**: Converts legacy errors to structured responses
3. **Data Transformation**: Converts legacy data structures to typed responses
4. **Graceful Degradation**: Handles missing or changed function signatures

This implementation serves as a bridge during the transition period and can be
replaced with a more optimized version once the legacy code is fully migrated.
"""
from __future__ import annotations

import logging
from typing import Any
from pydantic import ValidationError

from .protocols import AgentError
from .types import AgentSummary, ProposedReview, TakeoffRequest, TakeoffResponse

logger = logging.getLogger(__name__)


class DefaultTakeoffAgent:
    """Default implementation of the TakeoffAgent protocol.
    
    This adapter provides a stable interface between the new typed contract
    and the existing legacy implementation. It handles parameter adaptation,
    error conversion, and data transformation.
    """

    def run(self, req: TakeoffRequest) -> TakeoffResponse:
        """Run the takeoff agent using the legacy implementation.
        
        This method adapts the new typed request to the existing function
        signatures and converts the legacy response to the typed format.
        """
        # Runtime guard: Validate request structure early
        try:
            req = TakeoffRequest.model_validate(req)  # idempotent + early fail
        except ValidationError as e:
            # Bubble a clean message; exception handler will format it
            raise ValueError(f"Invalid TakeoffRequest: {e}") from e
        
        try:
            # 1) Detect and extract using existing pipeline
            logger.info(f"Starting takeoff for session {req.session_id}")

            # Adapt request parameters to legacy function signatures
            extract = self._run_legacy_extract(req)

            warnings: list[str] = []

            # 2) Ensure ground sampler is available
            ground_sampler = self._setup_ground_sampler(extract, warnings)

            # 3) Process depth calculations for each network
            self._process_network_depths(extract, ground_sampler, warnings)

            # 4) Build payload using existing writer
            payload = self._build_payload(extract)

            # 5) Generate summary statistics
            summary = self._generate_summary(extract)

            logger.info(f"Takeoff completed for session {req.session_id}: {summary.pipes_total} pipes")

            # Runtime guard: Validate response structure
            try:
                response = TakeoffResponse(
                    proposed_review=ProposedReview(payload=payload),
                    summary=summary,
                    warnings=warnings,
                )
                # Validate the response structure
                TakeoffResponse.model_validate(response.model_dump())
                return response
            except ValidationError as e:
                logger.error(f"Response validation failed: {e}")
                raise ValueError(f"Invalid TakeoffResponse structure: {e}") from e

        except Exception as e:
            logger.error(f"Takeoff failed for session {req.session_id}: {e!s}")
            # Runtime guard: Validate error response structure
            try:
                error_response = TakeoffResponse(
                    proposed_review=None,
                    summary=AgentSummary(pipes_total=0, qa_flags={}),
                    warnings=[],  # Initialize empty warnings for error case
                    error=str(e)
                )
                # Validate the error response structure
                TakeoffResponse.model_validate(error_response.model_dump())
                return error_response
            except ValidationError as validation_error:
                logger.error(f"Error response validation failed: {validation_error}")
                # Fallback to basic response if validation fails
                return TakeoffResponse(
                    proposed_review=None,
                    summary=AgentSummary(pipes_total=0, qa_flags={}),
                    warnings=warnings,
                    error=f"Takeoff failed: {e!s} (validation error: {validation_error})"
                )

    def _run_legacy_extract(self, req: TakeoffRequest) -> Any:
        """Run the legacy extract pipeline with adapted parameters."""
        # Import adapters
        from backend.app.agent.adapters import extract_any, extract_via_route
        
        # Determine file path
        file_path = None
        temp_file = None
        
        try:
            if req.upload_file:
                # Save uploaded file temporarily
                import os
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(req.upload_file)
                    file_path = tmp_file.name
                    temp_file = file_path
            else:
                # Use existing file reference
                file_path = req.file_ref

            # Call the canonical extract entrypoint directly
            logger.info(f"Running extract pipeline on: {file_path}")
            
            from backend.app.services import detectors
            extract_result = detectors.run_extract(
                file_ref=file_path,
                max_pages=req.options.max_pages
            )
            
            # extract_result is a dict with 'networks' and optional 'surface'
            networks = extract_result.get('networks', {})
            surface = extract_result.get('surface')
            
            logger.info(f"Extract complete: {len(networks)} networks, surface={'yes' if surface else 'no'}")
            
            # Wrap in ExtractPack-compatible object
            class _ExtractWrapper:
                """Wrapper to make run_extract result compatible with ExtractPack interface."""
                def __init__(self, networks, surface):
                    self.networks = networks
                    self.surface = surface
                    self.raw = {"networks": networks, "surface": surface}
                    
                def to_payload_networks(self):
                    return self.networks
                    
                def collect_qa_counts(self):
                    # Aggregate QA flags from all networks
                    qa_counts = {}
                    for network_name, network_data in self.networks.items():
                        qa_flags = network_data.get('qa_flags', [])
                        for flag in qa_flags:
                            # Properly serialize QA flag
                            if isinstance(flag, str):
                                flag_key = flag
                            elif isinstance(flag, dict):
                                flag_key = flag.get('code', str(flag))
                            elif hasattr(flag, 'code'):
                                # QAFlag object - use code as key
                                flag_key = flag.code
                            else:
                                flag_key = str(flag)
                            
                            qa_counts[flag_key] = qa_counts.get(flag_key, 0) + 1
                    return qa_counts
            
            extract = _ExtractWrapper(networks, surface)
            logger.info("Extract pipeline succeeded")
            return extract

        finally:
            # Clean up temporary file if created
            if temp_file:
                try:
                    import os
                    os.unlink(temp_file)
                except OSError:
                    pass

    def _setup_ground_sampler(self, extract: Any, warnings: list[str]) -> Any:
        """Set up ground elevation sampler with graceful fallbacks."""
        try:
            from backend.app.services.earthwork_surface import make_ground_sampler

            # Handle ExtractPack wrapper - extract data from either the wrapper or raw object
            profile_gl = None
            surface = None
            constant = None
            
            # Try to get surface from ExtractPack wrapper
            if hasattr(extract, "surface"):
                surface = extract.surface
            
            # Try to get profile_gl and constant from raw object
            raw_extract = getattr(extract, "raw", extract)
            profile_gl = getattr(raw_extract, "profile_gl", None)
            if constant is None:
                constant = getattr(raw_extract, "default_ground_elev", None)

            ground_sampler = make_ground_sampler(
                profile_gl=profile_gl,
                surface=surface,
                constant=constant
            )

            return ground_sampler

        except Exception as e:
            logger.warning(f"Ground sampler setup failed: {e!s}")
            warnings.append(f"Ground sampler setup failed: {e!s}")

            # Return a fallback sampler
            return self._create_fallback_sampler()

    def _create_fallback_sampler(self) -> Any:
        """Create a fallback ground sampler when the primary one fails."""
        def fallback_sampler(s_profile):
            # Simple fallback: return a constant elevation
            return 100.0  # Default ground elevation

        return fallback_sampler

    def _process_network_depths(self, extract: Any, ground_sampler: Any, warnings: list[str]) -> None:
        """Process depth calculations for each utility network."""
        try:
            from backend.app.services.detectors.depth import summarize_depth

            # Handle ExtractPack wrapper - get networks from either wrapper or raw object
            networks = {}
            if hasattr(extract, "networks"):
                networks = extract.networks
            else:
                networks = getattr(extract, "networks", {})

            # Process each network type
            for net_key in ("sanitary", "storm", "water"):
                # Handle both dict and object access
                network = networks.get(net_key) if isinstance(networks, dict) else None
                if not network:
                    continue

                # Get pipes - handle both dict and object structures
                pipes = getattr(network, "pipes", None) or (network.get("pipes") if isinstance(network, dict) else None)
                if not pipes:
                    continue

                for pipe in pipes:
                    try:
                        # Extract pipe profile - handle both dict and object
                        s_profile = getattr(pipe, "s_profile", None) or getattr(pipe, "profile", None) or (pipe.get("s_profile") if isinstance(pipe, dict) else None)
                        if not s_profile:
                            continue

                        # Get material and diameter - handle both dict and object
                        mat = getattr(pipe, "mat", None) or (pipe.get("mat") if isinstance(pipe, dict) else None)
                        dia_in = getattr(pipe, "dia_in", None) or (pipe.get("dia_in") if isinstance(pipe, dict) else None)

                        # Sample depth along the pipe run
                        samples = self._sample_pipe_depth(
                            s_profile=s_profile,
                            ground_sampler=ground_sampler,
                            material=mat,
                            dia_in=dia_in
                        )

                        # Summarize depth statistics
                        summary = summarize_depth(samples, net_key)
                        
                        # Determine ground source used for this pipe
                        ground_source_used = "unknown"
                        if hasattr(extract, "raw"):
                            raw = extract.raw
                            if hasattr(raw, "profile_gl") and raw.profile_gl:
                                ground_source_used = "profile"
                            elif hasattr(raw, "surface") and raw.surface:
                                ground_source_used = "surface"
                            elif hasattr(raw, "default_ground_elev") and raw.default_ground_elev:
                                ground_source_used = "constant"

                        # Update pipe with depth information - handle both dict and object
                        if isinstance(pipe, dict):
                            pipe["avg_depth_ft"] = summary.avg_depth_ft
                            pipe.setdefault("extra", {}).update({
                                "min_depth_ft": summary.min_depth_ft,
                                "max_depth_ft": summary.max_depth_ft,
                                "p95_depth_ft": summary.p95_depth_ft,
                                "buckets_lf": summary.buckets_lf,
                                "trench_volume_cy": summary.trench_volume_cy,
                                "cover_ok": summary.cover_ok,
                                "deep_excavation": summary.deep_excavation,
                                "ground_source": ground_source_used,  # Add transparency
                            })
                        else:
                            setattr(pipe, "avg_depth_ft", summary.avg_depth_ft)
                            extra = getattr(pipe, "extra", None)
                            if extra is None:
                                extra = {}
                                setattr(pipe, "extra", extra)
                            extra.update({
                                "min_depth_ft": summary.min_depth_ft,
                                "max_depth_ft": summary.max_depth_ft,
                                "p95_depth_ft": summary.p95_depth_ft,
                                "buckets_lf": summary.buckets_lf,
                                "trench_volume_cy": summary.trench_volume_cy,
                                "cover_ok": summary.cover_ok,
                                "deep_excavation": summary.deep_excavation,
                                "ground_source": ground_source_used,  # Add transparency
                            })

                    except Exception as e:
                        logger.warning(f"Depth processing failed for pipe: {e!s}")
                        warnings.append(f"Depth processing failed for pipe: {e!s}")

        except Exception as e:
            logger.warning(f"Network depth processing failed: {e!s}")
            warnings.append(f"Network depth processing failed: {e!s}")

    def _sample_pipe_depth(self, s_profile: Any, ground_sampler: Any, material: str, dia_in: float) -> list[float]:
        """Sample depth along a pipe profile."""
        try:
            from backend.app.services.detectors.depth import sample_depth_along_run

            samples = sample_depth_along_run(
                s_profile=s_profile,
                ground_at_s=ground_sampler,
                material=material,
                dia_in=dia_in,
                n_samples=20
            )

            return samples

        except Exception as e:
            logger.warning(f"Depth sampling failed: {e!s}")
            # Return fallback samples
            return [3.0] * 20  # Default 3ft depth

    def _build_payload(self, extract: Any) -> dict[str, Any]:
        """Build the payload using existing writer logic."""
        try:
            # Runtime guard: Validate extract structure
            if extract is None:
                raise ValueError("Extract result is None - legacy pipeline failed")
            
            # Use ExtractPack's to_payload_networks method
            if hasattr(extract, "to_payload_networks") and callable(extract.to_payload_networks):
                payload = {"networks": extract.to_payload_networks()}
                # Validate payload structure
                if not isinstance(payload, dict) or "networks" not in payload:
                    raise ValueError("Invalid payload structure from to_payload_networks()")
                return payload
            elif hasattr(extract, "networks"):
                # Manual payload construction
                networks = {}
                for net_key, network in extract.networks.items():
                    networks[net_key] = {
                        "pipes": [
                            {
                                "id": getattr(pipe, "id", f"{net_key}_{i}"),
                                "mat": getattr(pipe, "mat", "unknown"),
                                "dia_in": getattr(pipe, "dia_in", 0),
                                "length_ft": getattr(pipe, "length_ft", 0),
                                "avg_depth_ft": getattr(pipe, "avg_depth_ft", 0),
                                "extra": getattr(pipe, "extra", {})
                            }
                            for i, pipe in enumerate(getattr(network, "pipes", []))
                        ]
                    }
                return {"networks": networks}
            else:
                # Fallback payload
                return {"networks": {}}

        except Exception as e:
            logger.warning(f"Payload building failed: {e!s}")
            return {"networks": {}}

    def _generate_summary(self, extract: Any) -> AgentSummary:
        """Generate summary statistics with pipeline transparency info."""
        try:
            # Runtime guard: Validate extract structure
            if extract is None:
                raise ValueError("Extract result is None - cannot generate summary")
            
            # Count total pipes across all networks
            pipes_total = 0
            qa_flags = {}

            # Handle ExtractPack wrapper - get networks
            networks = {}
            if hasattr(extract, "networks"):
                networks = extract.networks
            else:
                networks = getattr(extract, "networks", {})
            
            # Validate networks structure
            if not isinstance(networks, dict):
                raise ValueError("Invalid networks structure in extract result")
            
            for net_key in ("sanitary", "storm", "water"):
                network = networks.get(net_key) if isinstance(networks, dict) else None
                if network:
                    # Handle both dict and object structures
                    pipes = getattr(network, "pipes", None) or (network.get("pipes") if isinstance(network, dict) else None)
                    pipes_total += len(pipes or [])

            # Collect QA flags using ExtractPack's method
            if hasattr(extract, "collect_qa_counts") and callable(extract.collect_qa_counts):
                qa_flags = extract.collect_qa_counts()
            elif hasattr(extract, "qa_flags"):
                qa_flags = extract.qa_flags

            # Collect pipeline transparency information
            from backend.app.core.config import settings
            from .types import PipelineInfo
            
            # Determine ground source used
            ground_source = "unknown"
            if hasattr(extract, "raw"):
                raw = extract.raw
                if hasattr(raw, "profile_gl") and raw.profile_gl:
                    ground_source = "profile"
                elif hasattr(raw, "surface") and raw.surface:
                    ground_source = "surface"
                elif hasattr(raw, "default_ground_elev") and raw.default_ground_elev:
                    ground_source = "constant"
            
            # Create pipeline info
            pipeline_info = PipelineInfo(
                apryse_enabled=settings.APR_USE_APRYSE,
                llm_enabled=True,  # Always true for our vision-based detector
                llm_model=settings.VISION_MODEL,
                ground_source=ground_source,
                prompt_token_count=None,  # Will be populated by LLM wrapper in future
                completion_token_count=None
            )

            # Runtime guard: Validate summary structure
            try:
                summary = AgentSummary(
                    pipes_total=pipes_total,
                    qa_flags=qa_flags,
                    pipeline=pipeline_info
                )
                # Validate the summary structure
                AgentSummary.model_validate(summary.model_dump())
                return summary
            except ValidationError as e:
                logger.error(f"Summary validation failed: {e}")
                raise ValueError(f"Invalid AgentSummary structure: {e}") from e

        except Exception as e:
            logger.warning(f"Summary generation failed: {e!s}")
            from .types import PipelineInfo
            from backend.app.core.config import settings
            return AgentSummary(
                pipes_total=0, 
                qa_flags={},
                pipeline=PipelineInfo(
                    apryse_enabled=settings.APR_USE_APRYSE,
                    llm_enabled=True,
                    llm_model=settings.VISION_MODEL,
                    ground_source="unknown"
                )
            )


# Factory function for creating the default agent
def create_default_agent() -> DefaultTakeoffAgent:
    """Create a new instance of the default takeoff agent."""
    return DefaultTakeoffAgent()
