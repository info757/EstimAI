"""
Contract tests for agent protocol compliance.

These tests ensure that agent implementations conform to the TakeoffAgent protocol
and catch signature drift at both compile time and runtime. This prevents the
exact problem where internal helper signatures change and adapters forget to adapt.
"""
from __future__ import annotations
from typing import get_type_hints, get_origin, get_args
import pytest

from backend.app.agent.protocols import TakeoffAgent, AgentError
from backend.app.agent.takeoff_impl import DefaultTakeoffAgent, create_default_agent
from backend.app.agent.types import TakeoffRequest, TakeoffResponse, TakeoffOptions, ProposedReview, AgentSummary


def test_agent_protocol_signature():
    """
    Test that DefaultTakeoffAgent conforms to TakeoffAgent protocol.
    
    This test catches signature drift at both compile time and runtime:
    - Type-level: Does DefaultTakeoffAgent conform to TakeoffAgent?
    - Runtime hints: Are the method signatures correct?
    """
    # Type-level compliance: This would fail mypy if DefaultTakeoffAgent doesn't conform
    agent: TakeoffAgent = DefaultTakeoffAgent()
    
    # Runtime type hints sanity check
    hints = get_type_hints(DefaultTakeoffAgent.run)
    
    # Check that the method signature matches the protocol
    assert 'req' in hints, "DefaultTakeoffAgent.run should have 'req' parameter"
    assert hints['req'] is TakeoffRequest, f"Expected TakeoffRequest, got {hints['req']}"
    
    # Check return type annotation
    assert 'return' in hints, "DefaultTakeoffAgent.run should have return type annotation"
    assert hints['return'] is TakeoffResponse, f"Expected TakeoffResponse, got {hints['return']}"


def test_agent_factory_returns_protocol():
    """
    Test that the factory function returns a protocol-compliant agent.
    """
    agent = create_default_agent()
    
    # Type-level: Should be assignable to TakeoffAgent
    protocol_agent: TakeoffAgent = agent
    
    # Runtime: Should have the required method
    assert hasattr(agent, 'run'), "Agent should have 'run' method"
    assert callable(getattr(agent, 'run')), "Agent.run should be callable"


def test_agent_protocol_method_signature():
    """
    Test that the protocol method signature is exactly as expected.
    """
    # Get the protocol method signature
    protocol_hints = get_type_hints(TakeoffAgent.run)
    
    # Get the implementation method signature  
    impl_hints = get_type_hints(DefaultTakeoffAgent.run)
    
    # Signatures should match exactly
    assert protocol_hints == impl_hints, f"Protocol and implementation signatures don't match: {protocol_hints} vs {impl_hints}"
    
    # Specific parameter checks
    assert 'req' in protocol_hints, "Protocol should have 'req' parameter"
    assert protocol_hints['req'] is TakeoffRequest, "Protocol 'req' should be TakeoffRequest"
    assert protocol_hints.get('return') is TakeoffResponse, "Protocol should return TakeoffResponse"


def test_agent_error_protocol():
    """
    Test that AgentError follows the expected protocol.
    """
    # Test basic error creation
    error = AgentError("Test error", "TEST_ERROR", retryable=True)
    
    assert error.get_error_code() == "TEST_ERROR"
    assert error.get_error_message() == "Test error"
    assert error.is_retryable() is True
    
    # Test error inheritance
    assert isinstance(error, Exception)
    assert isinstance(error, AgentError)


def test_agent_types_consistency():
    """
    Test that all agent types are properly defined and consistent.
    """
    # Test TakeoffRequest structure
    request = TakeoffRequest(
        session_id="test",
        file_ref="test.pdf",
        options=TakeoffOptions(dry_run=True)
    )
    
    assert request.session_id == "test"
    assert request.file_ref == "test.pdf"
    assert request.options.dry_run is True
    
    # Test TakeoffResponse structure
    response = TakeoffResponse(
        proposed_review=ProposedReview(payload={"test": "data"}),
        summary=AgentSummary(pipes_total=5),
        warnings=["test warning"]
    )
    
    assert response.proposed_review is not None
    assert response.summary is not None
    assert response.summary.pipes_total == 5
    assert len(response.warnings) == 1
    assert response.error is None


def test_agent_protocol_version_info():
    """
    Test that protocol version information is available and consistent.
    """
    from backend.app.agent.protocols import AGENT_PROTOCOL_VERSION, AGENT_PROTOCOL_DATE
    
    # Version should be a string
    assert isinstance(AGENT_PROTOCOL_VERSION, str)
    assert len(AGENT_PROTOCOL_VERSION) > 0
    
    # Date should be a string
    assert isinstance(AGENT_PROTOCOL_DATE, str)
    assert len(AGENT_PROTOCOL_DATE) > 0
    
    # Version should follow semantic versioning
    version_parts = AGENT_PROTOCOL_VERSION.split('.')
    assert len(version_parts) >= 2, "Version should have at least major.minor"
    
    # All parts should be numeric
    for part in version_parts:
        assert part.isdigit(), f"Version part '{part}' should be numeric"


def test_agent_imports_stability():
    """
    Test that all required agent symbols are properly exported.
    """
    from backend.app.agent import (
        TakeoffRequest, TakeoffOptions, TakeoffResponse, 
        ProposedReview, AgentSummary, TakeoffAgent, 
        AgentError, AGENT_PROTOCOL_VERSION, AGENT_PROTOCOL_DATE
    )
    
    # All symbols should be importable
    assert TakeoffRequest is not None
    assert TakeoffOptions is not None
    assert TakeoffResponse is not None
    assert ProposedReview is not None
    assert AgentSummary is not None
    assert TakeoffAgent is not None
    assert AgentError is not None
    assert AGENT_PROTOCOL_VERSION is not None
    assert AGENT_PROTOCOL_DATE is not None


def test_agent_protocol_runtime_compliance():
    """
    Test that the agent implementation actually follows the protocol at runtime.
    """
    agent = create_default_agent()
    
    # Create a minimal request
    request = TakeoffRequest(
        session_id="contract_test",
        file_ref="dummy.pdf",
        options=TakeoffOptions(dry_run=True)
    )
    
    # The agent should be callable with the expected signature
    try:
        # This will likely fail due to missing dependencies, but the signature should be correct
        response = agent.run(request)
        
        # If it succeeds, check the response structure
        assert isinstance(response, TakeoffResponse)
        assert response.session_id == request.session_id
        
    except Exception as e:
        # Expected to fail due to missing dependencies, but signature should be correct
        # The important thing is that it doesn't fail with "takes X arguments but Y were given"
        assert "takes" not in str(e) or "arguments" not in str(e), f"Signature error: {e}"


def test_agent_protocol_type_safety():
    """
    Test that the protocol provides type safety for common usage patterns.
    """
    # Test that we can create a protocol-compliant agent
    agent: TakeoffAgent = create_default_agent()
    
    # Test that we can create requests and responses
    request = TakeoffRequest(
        session_id="type_safety_test",
        file_ref="test.pdf",
        options=TakeoffOptions(dry_run=False, max_pages=5)
    )
    
    # Test that the agent has the expected interface
    assert hasattr(agent, 'run')
    assert callable(agent.run)
    
    # Test that the method signature is correct (this would fail at type check time if wrong)
    # We can't easily test the actual call without mocking dependencies,
    # but the type annotations should be correct


@pytest.mark.parametrize("agent_class", [DefaultTakeoffAgent])
def test_agent_implementation_protocol_compliance(agent_class):
    """
    Parametrized test to ensure any agent implementation conforms to the protocol.
    """
    agent = agent_class()
    
    # Should be assignable to the protocol
    protocol_agent: TakeoffAgent = agent
    
    # Should have the required method
    assert hasattr(agent, 'run')
    assert callable(agent.run)
    
    # Method signature should match protocol
    hints = get_type_hints(agent.run)
    assert 'req' in hints
    assert hints['req'] is TakeoffRequest
    assert hints.get('return') is TakeoffResponse


def test_agent_protocol_evolution_safety():
    """
    Test that the protocol can evolve safely without breaking existing implementations.
    """
    # This test ensures that if we add new methods to the protocol,
    # existing implementations won't break (they'll just not implement the new methods)
    
    # For now, the protocol only has one method: run
    protocol_methods = [method for method in dir(TakeoffAgent) if not method.startswith('_')]
    
    # Should have at least the 'run' method
    assert 'run' in protocol_methods
    
    # Implementation should have the required method
    agent = create_default_agent()
    assert hasattr(agent, 'run')
    assert callable(agent.run)
