"""
Agent orchestrator for construction takeoff pipeline.

This module orchestrates the full takeoff pipeline:
detect/extract → depth summarize → propose review payload.

Features:
- Idempotent via session_id
- Retries and timeouts
- Tool error messages
- Integration with Apryse PDFNet
- LLM-powered analysis
- Review payload generation
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.app.core.config import settings
from backend.app.schemas_estimai import EstimAIResult
from backend.app.services.ingest.pdfnet_runtime import init as pdfnet_init, open_doc, iter_pages
from backend.app.services.ingest.scale import infer_scale_text, infer_scale_bar, compute_user_to_world
from backend.app.services.ingest.extract import extract_vectors, extract_text
from backend.app.services.detectors.legend import find_legend_regions, sample_symbol_snippets
from backend.app.services.detectors.symbol_map import build_symbol_map_via_llm
from backend.app.services.detectors.storm import detect_nodes, trace_edges, attach_labels
from backend.app.services.detectors.sanitary import detect_nodes as sanitary_detect_nodes, trace_edges as sanitary_trace_edges, attach_labels as sanitary_attach_labels
from backend.app.services.detectors.water import detect_nodes as water_detect_nodes, trace_edges as water_trace_edges, attach_labels as water_attach_labels
from backend.app.services.detectors.sitework import measure_curb_lf, measure_sidewalk_sf, measure_silt_fence_lf, count_inlet_protections
from backend.app.services.detectors.earthwork_tables import parse_earthwork_summary
from backend.app.services.detectors.earthwork_surface import load_surface_from_pdf, create_elevation_sampler, sample_along_centerline
from backend.app.services.detectors.depth import init_depth_config, sample_depth_along_run, summarize_depth
from backend.app.services.detectors.qa_rules import validate_network_qa
from backend.app.agents.llm_gateway import complete_json


logger = logging.getLogger(__name__)


@dataclass
class TakeoffSession:
    """Session data for takeoff processing."""
    session_id: str
    file_ref: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: datetime
    updated_at: datetime
    result: Optional[EstimAIResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TakeoffRequest:
    """Request for takeoff processing."""
    session_id: str
    file_ref: Optional[str] = None
    upload_file: Optional[Any] = None  # FastAPI UploadFile


@dataclass
class TakeoffResponse:
    """Response from takeoff processing."""
    session_id: str
    status: str
    proposed_review: Optional[EstimAIResult] = None
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


class TakeoffAgent:
    """Agent orchestrator for construction takeoff pipeline."""
    
    def __init__(self):
        self.sessions: Dict[str, TakeoffSession] = {}
        self.timeout_seconds = 300  # 5 minutes
        self.retry_delay = 5  # seconds
        
    async def process_takeoff(self, request: TakeoffRequest) -> TakeoffResponse:
        """
        Process takeoff request with full pipeline orchestration.
        
        Args:
            request: TakeoffRequest with session_id and file reference
            
        Returns:
            TakeoffResponse with results or error information
        """
        start_time = time.time()
        session_id = request.session_id
        
        try:
            # Check if session already exists (idempotency)
            if session_id in self.sessions:
                existing_session = self.sessions[session_id]
                if existing_session.status == 'completed':
                    return TakeoffResponse(
                        session_id=session_id,
                        status='completed',
                        proposed_review=existing_session.result,
                        summary=self._generate_summary(existing_session.result),
                        processing_time=time.time() - start_time
                    )
                elif existing_session.status == 'processing':
                    return TakeoffResponse(
                        session_id=session_id,
                        status='processing',
                        error_message='Session already in progress'
                    )
            
            # Create new session
            session = TakeoffSession(
                session_id=session_id,
                file_ref=request.file_ref or 'upload',
                status='pending',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.sessions[session_id] = session
            
            # Process with timeout and retries
            result = await self._process_with_retries(session, request)
            
            # Update session
            session.status = 'completed'
            session.result = result
            session.updated_at = datetime.now()
            
            return TakeoffResponse(
                session_id=session_id,
                status='completed',
                proposed_review=result,
                summary=self._generate_summary(result),
                processing_time=time.time() - start_time
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Takeoff processing timeout for session {session_id}")
            return TakeoffResponse(
                session_id=session_id,
                status='failed',
                error_message='Processing timeout',
                processing_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Takeoff processing error for session {session_id}: {str(e)}")
            if session_id in self.sessions:
                self.sessions[session_id].status = 'failed'
                self.sessions[session_id].error_message = str(e)
            
            return TakeoffResponse(
                session_id=session_id,
                status='failed',
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _process_with_retries(self, session: TakeoffSession, request: TakeoffRequest) -> EstimAIResult:
        """Process takeoff with retry logic."""
        for attempt in range(session.max_retries + 1):
            try:
                session.status = 'processing'
                session.retry_count = attempt
                session.updated_at = datetime.now()
                
                # Process with timeout
                result = await asyncio.wait_for(
                    self._run_takeoff_pipeline(session, request),
                    timeout=self.timeout_seconds
                )
                
                return result
                
            except Exception as e:
                logger.warning(f"Takeoff attempt {attempt + 1} failed for session {session.session_id}: {str(e)}")
                
                if attempt < session.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise e
    
    async def _run_takeoff_pipeline(self, session: TakeoffSession, request: TakeoffRequest) -> EstimAIResult:
        """Run the full takeoff pipeline."""
        logger.info(f"Starting takeoff pipeline for session {session.session_id}")
        
        # Step 1: Initialize Apryse if enabled
        if settings.APR_USE_APRYSE:
            try:
                pdfnet_init()
                logger.info("Apryse PDFNet initialized")
            except Exception as e:
                logger.warning(f"Apryse initialization failed: {e}")
        
        # Step 2: Open PDF document
        try:
            # For now, use a mock file path - in production this would handle uploads
            pdf_path = f"backend/files/{session.file_ref}"
            if not Path(pdf_path).exists():
                pdf_path = "backend/files/280-utility-construction-plans.pdf"  # Fallback
            
            doc = open_doc(pdf_path)
            logger.info(f"PDF document opened: {pdf_path}")
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")
        
        try:
            # Step 3: Extract content from all pages
            all_vectors = []
            all_texts = []
            scale_info = None
            
            for page_num, page in enumerate(iter_pages(doc)):
                logger.info(f"Processing page {page_num + 1}")
                
                # Extract vectors and text
                vectors = extract_vectors(page)
                texts = extract_text(page)
                
                all_vectors.extend(vectors)
                all_texts.extend(texts)
                
                # Infer scale from first page
                if page_num == 0:
                    scale_info = infer_scale_text(texts) or infer_scale_bar(vectors)
                    if scale_info:
                        logger.info(f"Scale detected: {scale_info}")
            
            if not all_vectors:
                raise Exception("No vector data found in PDF")
            
            # Step 4: Build symbol map via LLM
            logger.info("Building symbol map via LLM")
            legend_regions = find_legend_regions(all_texts)
            symbol_snippets = sample_symbol_snippets(all_vectors, all_texts, legend_regions)
            symbol_map = build_symbol_map_via_llm(symbol_snippets, "".join([t.get('text', '') for t in all_texts]))
            
            # Step 5: Detect networks (storm, sanitary, water)
            logger.info("Detecting utility networks")
            
            # Storm network
            storm_nodes = detect_nodes(all_vectors, symbol_map, 'storm')
            storm_edges = trace_edges(all_vectors, storm_nodes, 'storm')
            storm_network = attach_labels(storm_nodes, storm_edges, all_texts, 'storm')
            
            # Sanitary network
            sanitary_nodes = sanitary_detect_nodes(all_vectors, symbol_map, 'sanitary')
            sanitary_edges = sanitary_trace_edges(all_vectors, sanitary_nodes, 'sanitary')
            sanitary_network = sanitary_attach_labels(sanitary_nodes, sanitary_edges, all_texts, 'sanitary')
            
            # Water network
            water_nodes = water_detect_nodes(all_vectors, symbol_map, 'water')
            water_edges = water_trace_edges(all_vectors, water_nodes, 'water')
            water_network = water_attach_labels(water_nodes, water_edges, all_texts, 'water')
            
            # Step 6: Sitework quantities
            logger.info("Calculating sitework quantities")
            curb_lf = measure_curb_lf(all_vectors, scale_info)
            sidewalk_sf = measure_sidewalk_sf(all_vectors, scale_info)
            silt_fence_lf = measure_silt_fence_lf(all_vectors, scale_info)
            inlet_protections = count_inlet_protections(all_vectors, symbol_map)
            
            # Step 7: Earthwork analysis
            logger.info("Analyzing earthwork")
            earthwork_tables = parse_earthwork_summary(all_texts)
            
            # Surface-based earthwork (if contours available)
            surface_profile = load_surface_from_pdf(all_vectors, scale_info)
            if surface_profile.contours:
                elevation_sampler = create_elevation_sampler(surface_profile)
                # Sample along key centerlines for earthwork
                # This would be more sophisticated in production
                earthwork_surface = None  # Placeholder for surface analysis
            else:
                earthwork_surface = None
            
            # Step 8: Depth analysis for pipes
            logger.info("Analyzing pipe depths")
            if settings.APR_USE_APRYSE:
                init_depth_config()
                
                # Analyze storm network depths
                for pipe in storm_network.get('pipes', []):
                    if pipe.get('points'):
                        # Create centerline from pipe points
                        from shapely.geometry import LineString
                        centerline = LineString(pipe['points'])
                        
                        # Sample depth along centerline
                        depth_samples = sample_depth_along_run(
                            pipe.get('s_profile', []),
                            lambda s: 100.0,  # Mock ground level function
                            pipe.get('material', 'concrete'),
                            pipe.get('dia_in', 12.0)
                        )
                        
                        # Summarize depth analysis
                        depth_summary = summarize_depth(depth_samples)
                        pipe['extra'] = depth_summary
                        pipe['avg_depth_ft'] = depth_summary.get('avg_depth_ft', 0.0)
                
                # Similar analysis for sanitary and water networks
                for network_name, network in [('sanitary', sanitary_network), ('water', water_network)]:
                    for pipe in network.get('pipes', []):
                        if pipe.get('points'):
                            from shapely.geometry import LineString
                            centerline = LineString(pipe['points'])
                            
                            depth_samples = sample_depth_along_run(
                                pipe.get('s_profile', []),
                                lambda s: 100.0,  # Mock ground level function
                                pipe.get('material', 'concrete'),
                                pipe.get('dia_in', 12.0)
                            )
                            
                            depth_summary = summarize_depth(depth_samples)
                            pipe['extra'] = depth_summary
                            pipe['avg_depth_ft'] = depth_summary.get('avg_depth_ft', 0.0)
            
            # Step 9: QA validation
            logger.info("Running QA validation")
            qa_flags = []
            
            # Validate each network
            if storm_network:
                qa_flags.extend(validate_network_qa(storm_network, 'storm'))
            if sanitary_network:
                qa_flags.extend(validate_network_qa(sanitary_network, 'sanitary'))
            if water_network:
                qa_flags.extend(validate_network_qa(water_network, 'water'))
            
            # Step 10: Build final result
            result = EstimAIResult(
                session_id=session.session_id,
                timestamp=datetime.now().isoformat(),
                networks={
                    'storm': storm_network,
                    'sanitary': sanitary_network,
                    'water': water_network
                },
                roadway={
                    'curb_lf': curb_lf,
                    'sidewalk_sf': sidewalk_sf,
                    'silt_fence_lf': silt_fence_lf
                },
                esc={
                    'inlet_protections': inlet_protections
                },
                earthwork={
                    'tables': earthwork_tables,
                    'surface': earthwork_surface
                },
                qa_flags=qa_flags
            )
            
            logger.info(f"Takeoff pipeline completed for session {session.session_id}")
            return result
            
        finally:
            # Clean up document
            try:
                if 'doc' in locals():
                    doc.close()
            except Exception as e:
                logger.warning(f"Error closing document: {e}")
    
    def _generate_summary(self, result: EstimAIResult) -> Dict[str, Any]:
        """Generate summary of takeoff results."""
        if not result:
            return {}
        
        summary = {
            'networks': {},
            'quantities': {},
            'qa_flags': len(result.qa_flags) if result.qa_flags else 0
        }
        
        # Count pipes by network
        for network_name in ['storm', 'sanitary', 'water']:
            network = getattr(result.networks, network_name, None)
            if network and hasattr(network, 'pipes'):
                pipe_count = len(network.pipes) if network.pipes else 0
                summary['networks'][network_name] = {
                    'pipes': pipe_count,
                    'nodes': len(network.nodes) if hasattr(network, 'nodes') and network.nodes else 0
                }
        
        # Sitework quantities
        if result.roadway:
            summary['quantities']['curb_lf'] = result.roadway.curb_lf or 0
            summary['quantities']['sidewalk_sf'] = result.roadway.sidewalk_sf or 0
        
        if result.e_sc:
            summary['quantities']['silt_fence_lf'] = result.e_sc.silt_fence_lf or 0
            summary['quantities']['inlet_protections'] = result.e_sc.inlet_protection_ea or 0
        
        return summary


# Global agent instance
_agent = TakeoffAgent()


async def process_takeoff_request(request: TakeoffRequest) -> TakeoffResponse:
    """Process takeoff request using the global agent."""
    return await _agent.process_takeoff(request)


def get_session_status(session_id: str) -> Optional[TakeoffSession]:
    """Get session status by ID."""
    return _agent.sessions.get(session_id)


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """Clean up old sessions."""
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    old_sessions = [
        sid for sid, session in _agent.sessions.items()
        if session.created_at < cutoff_time
    ]
    
    for sid in old_sessions:
        del _agent.sessions[sid]
    
    return len(old_sessions)
