"""
Unit tests for agent takeoff processing.

Tests the full agent loop with Apryse → LLM → Review pipeline,
including idempotency, timeouts, and error handling.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from backend.app.agent.takeoff import (
    TakeoffAgent, TakeoffRequest, TakeoffResponse, TakeoffSession,
    process_takeoff_request, get_session_status, cleanup_old_sessions
)
from backend.app.schemas_estimai import EstimAIResult


class TestTakeoffAgent:
    """Test cases for TakeoffAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = TakeoffAgent()
        self.test_session_id = "test-session-123"
        self.test_file_ref = "test-file.pdf"
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.sessions == {}
        assert self.agent.timeout_seconds == 300
        assert self.agent.retry_delay == 5
    
    @pytest.mark.asyncio
    async def test_process_takeoff_success(self):
        """Test successful takeoff processing."""
        # Mock the pipeline
        with patch.object(self.agent, '_run_takeoff_pipeline') as mock_pipeline:
            mock_result = EstimAIResult(
                session_id=self.test_session_id,
                timestamp=datetime.now().isoformat(),
                networks={},
                roadway={},
                esc={},
                earthwork={},
                qa_flags=[]
            )
            mock_pipeline.return_value = mock_result
            
            request = TakeoffRequest(
                session_id=self.test_session_id,
                file_ref=self.test_file_ref
            )
            
            response = await self.agent.process_takeoff(request)
            
            assert response.session_id == self.test_session_id
            assert response.status == 'completed'
            assert response.proposed_review == mock_result
            assert response.error_message is None
            assert response.processing_time is not None
    
    @pytest.mark.asyncio
    async def test_process_takeoff_idempotency(self):
        """Test idempotent processing."""
        # Create existing completed session
        existing_session = TakeoffSession(
            session_id=self.test_session_id,
            file_ref=self.test_file_ref,
            status='completed',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            result=EstimAIResult(
                session_id=self.test_session_id,
                timestamp=datetime.now().isoformat(),
                networks={},
                roadway={},
                esc={},
                earthwork={},
                qa_flags=[]
            )
        )
        self.agent.sessions[self.test_session_id] = existing_session
        
        request = TakeoffRequest(
            session_id=self.test_session_id,
            file_ref=self.test_file_ref
        )
        
        response = await self.agent.process_takeoff(request)
        
        assert response.status == 'completed'
        assert response.proposed_review == existing_session.result
        # Should not call pipeline again
        assert len(self.agent.sessions) == 1
    
    @pytest.mark.asyncio
    async def test_process_takeoff_processing_in_progress(self):
        """Test handling of in-progress session."""
        # Create in-progress session
        in_progress_session = TakeoffSession(
            session_id=self.test_session_id,
            file_ref=self.test_file_ref,
            status='processing',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.agent.sessions[self.test_session_id] = in_progress_session
        
        request = TakeoffRequest(
            session_id=self.test_session_id,
            file_ref=self.test_file_ref
        )
        
        response = await self.agent.process_takeoff(request)
        
        assert response.status == 'processing'
        assert response.error_message == 'Session already in progress'
    
    @pytest.mark.asyncio
    async def test_process_takeoff_timeout(self):
        """Test timeout handling."""
        with patch.object(self.agent, '_run_takeoff_pipeline') as mock_pipeline:
            mock_pipeline.side_effect = asyncio.TimeoutError()
            
            request = TakeoffRequest(
                session_id=self.test_session_id,
                file_ref=self.test_file_ref
            )
            
            response = await self.agent.process_takeoff(request)
            
            assert response.status == 'failed'
            assert 'timeout' in response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_process_takeoff_retry_logic(self):
        """Test retry logic with exponential backoff."""
        with patch.object(self.agent, '_run_takeoff_pipeline') as mock_pipeline:
            # First two calls fail, third succeeds
            mock_pipeline.side_effect = [
                Exception("First failure"),
                Exception("Second failure"),
                EstimAIResult(
                    session_id=self.test_session_id,
                    timestamp=datetime.now().isoformat(),
                    networks={},
                    roadway={},
                    esc={},
                    earthwork={},
                    qa_flags=[]
                )
            ]
            
            request = TakeoffRequest(
                session_id=self.test_session_id,
                file_ref=self.test_file_ref
            )
            
            response = await self.agent.process_takeoff(request)
            
            assert response.status == 'completed'
            assert mock_pipeline.call_count == 3
    
    @pytest.mark.asyncio
    async def test_process_takeoff_max_retries_exceeded(self):
        """Test handling when max retries exceeded."""
        with patch.object(self.agent, '_run_takeoff_pipeline') as mock_pipeline:
            mock_pipeline.side_effect = Exception("Persistent failure")
            
            request = TakeoffRequest(
                session_id=self.test_session_id,
                file_ref=self.test_file_ref
            )
            
            response = await self.agent.process_takeoff(request)
            
            assert response.status == 'failed'
            assert 'Persistent failure' in response.error_message
    
    def test_generate_summary(self):
        """Test summary generation."""
        result = EstimAIResult(
            session_id=self.test_session_id,
            timestamp=datetime.now().isoformat(),
            networks={
                'storm': Mock(pipes=[Mock(), Mock()], nodes=[Mock()]),
                'sanitary': Mock(pipes=[Mock()], nodes=[Mock(), Mock()]),
                'water': Mock(pipes=[], nodes=[])
            },
            roadway=Mock(curb_lf=1200.0, sidewalk_sf=2400.0, silt_fence_lf=800.0),
            esc=Mock(inlet_protections=8),
            earthwork={},
            qa_flags=[Mock(), Mock()]
        )
        
        summary = self.agent._generate_summary(result)
        
        assert summary['session_id'] == self.test_session_id
        assert summary['networks']['storm']['pipes'] == 2
        assert summary['networks']['sanitary']['pipes'] == 1
        assert summary['networks']['water']['pipes'] == 0
        assert summary['quantities']['curb_lf'] == 1200.0
        assert summary['qa_flags'] == 2


class TestTakeoffSession:
    """Test cases for TakeoffSession."""
    
    def test_session_creation(self):
        """Test session creation."""
        session = TakeoffSession(
            session_id="test-123",
            file_ref="test.pdf",
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert session.session_id == "test-123"
        assert session.file_ref == "test.pdf"
        assert session.status == "pending"
        assert session.result is None
        assert session.error_message is None
        assert session.retry_count == 0
        assert session.max_retries == 3


class TestTakeoffRequest:
    """Test cases for TakeoffRequest."""
    
    def test_request_creation(self):
        """Test request creation."""
        request = TakeoffRequest(
            session_id="test-123",
            file_ref="test.pdf"
        )
        
        assert request.session_id == "test-123"
        assert request.file_ref == "test.pdf"
        assert request.upload_file is None
    
    def test_request_with_upload(self):
        """Test request with upload file."""
        mock_file = Mock()
        request = TakeoffRequest(
            session_id="test-123",
            upload_file=mock_file
        )
        
        assert request.session_id == "test-123"
        assert request.file_ref is None
        assert request.upload_file == mock_file


class TestTakeoffResponse:
    """Test cases for TakeoffResponse."""
    
    def test_response_creation(self):
        """Test response creation."""
        response = TakeoffResponse(
            session_id="test-123",
            status="completed",
            processing_time=45.2
        )
        
        assert response.session_id == "test-123"
        assert response.status == "completed"
        assert response.proposed_review is None
        assert response.summary is None
        assert response.error_message is None
        assert response.processing_time == 45.2


class TestSessionManagement:
    """Test cases for session management functions."""
    
    def test_get_session_status(self):
        """Test getting session status."""
        agent = TakeoffAgent()
        session = TakeoffSession(
            session_id="test-123",
            file_ref="test.pdf",
            status="completed",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        agent.sessions["test-123"] = session
        
        retrieved = get_session_status("test-123")
        assert retrieved == session
        
        not_found = get_session_status("nonexistent")
        assert not_found is None
    
    def test_cleanup_old_sessions(self):
        """Test cleanup of old sessions."""
        agent = TakeoffAgent()
        
        # Create old session
        old_session = TakeoffSession(
            session_id="old-123",
            file_ref="old.pdf",
            status="completed",
            created_at=datetime.now() - timedelta(hours=25),
            updated_at=datetime.now() - timedelta(hours=25)
        )
        
        # Create recent session
        recent_session = TakeoffSession(
            session_id="recent-123",
            file_ref="recent.pdf",
            status="completed",
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now() - timedelta(hours=1)
        )
        
        agent.sessions["old-123"] = old_session
        agent.sessions["recent-123"] = recent_session
        
        # Clean up sessions older than 24 hours
        cleaned_count = cleanup_old_sessions(24)
        
        assert cleaned_count == 1
        assert "old-123" not in agent.sessions
        assert "recent-123" in agent.sessions


class TestGoldenFixtures:
    """Test cases using golden JSON fixtures."""
    
    def test_golden_fixture_loading(self):
        """Test loading golden JSON fixtures."""
        fixture_path = Path(__file__).parent / "fixtures" / "agent_takeoff_golden.json"
        
        if fixture_path.exists():
            with open(fixture_path, 'r') as f:
                golden_data = json.load(f)
            
            # Validate structure
            assert "session_id" in golden_data
            assert "status" in golden_data
            assert "proposed_review" in golden_data
            assert "summary" in golden_data
            
            # Validate proposed review structure
            proposed_review = golden_data["proposed_review"]
            assert "networks" in proposed_review
            assert "roadway" in proposed_review
            assert "esc" in proposed_review
            assert "earthwork" in proposed_review
            assert "qa_flags" in proposed_review
            
            # Validate networks
            networks = proposed_review["networks"]
            for network_name in ["storm", "sanitary", "water"]:
                assert network_name in networks
                network = networks[network_name]
                assert "pipes" in network
                assert "nodes" in network
                
                # Validate pipe structure
                for pipe in network["pipes"]:
                    assert "id" in pipe
                    assert "points" in pipe
                    assert "length_ft" in pipe
                    assert "dia_in" in pipe
                    assert "mat" in pipe
                    assert "avg_depth_ft" in pipe
                    assert "extra" in pipe
                    
                    # Validate depth analysis
                    extra = pipe["extra"]
                    assert "min_depth_ft" in extra
                    assert "max_depth_ft" in extra
                    assert "p95_depth_ft" in extra
                    assert "buckets_lf" in extra
                    assert "trench_volume_cy" in extra
                    assert "cover_ok" in extra
                    assert "deep_excavation" in extra
            
            # Validate summary structure
            summary = golden_data["summary"]
            assert "networks" in summary
            assert "quantities" in summary
            assert "qa_flags" in summary


class TestTimeoutHandling:
    """Test cases for timeout handling."""
    
    @pytest.mark.asyncio
    async def test_pipeline_timeout(self):
        """Test pipeline timeout handling."""
        agent = TakeoffAgent()
        agent.timeout_seconds = 0.1  # Very short timeout for testing
        
        with patch.object(agent, '_run_takeoff_pipeline') as mock_pipeline:
            async def slow_pipeline(*args, **kwargs):
                await asyncio.sleep(1.0)  # Longer than timeout
                return EstimAIResult(
                    session_id="test",
                    timestamp=datetime.now().isoformat(),
                    networks={},
                    roadway={},
                    esc={},
                    earthwork={},
                    qa_flags=[]
                )
            
            mock_pipeline.side_effect = slow_pipeline
            
            request = TakeoffRequest(
                session_id="timeout-test",
                file_ref="test.pdf"
            )
            
            response = await agent.process_takeoff(request)
            
            assert response.status == 'failed'
            assert 'timeout' in response.error_message.lower()


class TestErrorHandling:
    """Test cases for error handling."""
    
    @pytest.mark.asyncio
    async def test_pipeline_exception(self):
        """Test handling of pipeline exceptions."""
        agent = TakeoffAgent()
        
        with patch.object(agent, '_run_takeoff_pipeline') as mock_pipeline:
            mock_pipeline.side_effect = Exception("Pipeline error")
            
            request = TakeoffRequest(
                session_id="error-test",
                file_ref="test.pdf"
            )
            
            response = await agent.process_takeoff(request)
            
            assert response.status == 'failed'
            assert "Pipeline error" in response.error_message
    
    @pytest.mark.asyncio
    async def test_retry_with_different_errors(self):
        """Test retry logic with different error types."""
        agent = TakeoffAgent()
        
        with patch.object(agent, '_run_takeoff_pipeline') as mock_pipeline:
            # Different errors on each attempt
            mock_pipeline.side_effect = [
                Exception("Network error"),
                Exception("File error"),
                EstimAIResult(
                    session_id="test",
                    timestamp=datetime.now().isoformat(),
                    networks={},
                    roadway={},
                    esc={},
                    earthwork={},
                    qa_flags=[]
                )
            ]
            
            request = TakeoffRequest(
                session_id="retry-test",
                file_ref="test.pdf"
            )
            
            response = await agent.process_takeoff(request)
            
            assert response.status == 'completed'
            assert mock_pipeline.call_count == 3


class TestIdempotency:
    """Test cases for idempotency."""
    
    @pytest.mark.asyncio
    async def test_multiple_requests_same_session(self):
        """Test multiple requests with same session ID."""
        agent = TakeoffAgent()
        
        # First request
        request1 = TakeoffRequest(
            session_id="idempotent-test",
            file_ref="test.pdf"
        )
        
        with patch.object(agent, '_run_takeoff_pipeline') as mock_pipeline:
            mock_result = EstimAIResult(
                session_id="idempotent-test",
                timestamp=datetime.now().isoformat(),
                networks={},
                roadway={},
                esc={},
                earthwork={},
                qa_flags=[]
            )
            mock_pipeline.return_value = mock_result
            
            response1 = await agent.process_takeoff(request1)
            assert response1.status == 'completed'
            
            # Second request with same session ID
            request2 = TakeoffRequest(
                session_id="idempotent-test",
                file_ref="test.pdf"
            )
            
            response2 = await agent.process_takeoff(request2)
            assert response2.status == 'completed'
            assert response2.proposed_review == response1.proposed_review
            
            # Pipeline should only be called once
            assert mock_pipeline.call_count == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_same_session(self):
        """Test concurrent requests with same session ID."""
        agent = TakeoffAgent()
        
        async def make_request():
            request = TakeoffRequest(
                session_id="concurrent-test",
                file_ref="test.pdf"
            )
            return await agent.process_takeoff(request)
        
        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        
        # All responses should be the same
        for response in responses:
            assert response.status == 'completed'
            assert response.session_id == "concurrent-test"
        
        # Should only have one session in the agent
        assert len(agent.sessions) == 1
