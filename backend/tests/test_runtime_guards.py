"""
Test runtime guards for agent protocol compliance.

These tests verify that runtime guards catch signature drift and provide
friendly error messages instead of cryptic stack traces.
"""
from __future__ import annotations
import pytest
from pydantic import ValidationError

from backend.app.agent.takeoff_impl import DefaultTakeoffAgent
from backend.app.agent.types import TakeoffRequest, TakeoffResponse, TakeoffOptions


def test_runtime_guard_invalid_request():
    """Test that runtime guards catch invalid request structures."""
    agent = DefaultTakeoffAgent()
    
    # Test with invalid request structure
    with pytest.raises(ValueError, match="Invalid TakeoffRequest"):
        agent.run("invalid_request")  # type: ignore


def test_runtime_guard_missing_session_id():
    """Test that runtime guards catch missing required fields."""
    agent = DefaultTakeoffAgent()
    
    # Test with empty session_id but valid file_ref
    invalid_req = TakeoffRequest(
        session_id="",  # Empty session_id should be invalid
        file_ref="test.pdf",
        options=TakeoffOptions()
    )
    
    # This should pass validation but fail in the agent logic
    response = agent.run(invalid_req)
    assert response.error is not None
    assert "Invalid TakeoffRequest" not in response.error  # Should not be a validation error


def test_runtime_guard_valid_request():
    """Test that runtime guards allow valid requests."""
    agent = DefaultTakeoffAgent()
    
    # Test with valid request
    valid_req = TakeoffRequest(
        session_id="test_session",
        file_ref="test.pdf",
        options=TakeoffOptions()
    )
    
    # This should not raise validation errors
    response = agent.run(valid_req)
    assert isinstance(response, TakeoffResponse)
    # The response might fail due to missing files, but not due to validation


def test_runtime_guard_response_validation():
    """Test that runtime guards validate response structures."""
    agent = DefaultTakeoffAgent()
    
    # Test with valid request that should produce a valid response structure
    valid_req = TakeoffRequest(
        session_id="test_session",
        file_ref="test.pdf",
        options=TakeoffOptions()
    )
    
    response = agent.run(valid_req)
    
    # Response should be a valid TakeoffResponse
    assert isinstance(response, TakeoffResponse)
    assert hasattr(response, "proposed_review")
    assert hasattr(response, "summary")
    assert hasattr(response, "warnings")
    
    # Validate the response structure
    try:
        TakeoffResponse.model_validate(response.model_dump())
    except ValidationError as e:
        pytest.fail(f"Response validation failed: {e}")


def test_runtime_guard_error_response_validation():
    """Test that runtime guards validate error response structures."""
    agent = DefaultTakeoffAgent()
    
    # Test with request that will fail (file doesn't exist)
    req = TakeoffRequest(
        session_id="test_session",
        file_ref="nonexistent.pdf",
        options=TakeoffOptions()
    )
    
    response = agent.run(req)
    
    # Error response should still be valid
    assert isinstance(response, TakeoffResponse)
    assert response.error is not None
    
    # Validate the error response structure
    try:
        TakeoffResponse.model_validate(response.model_dump())
    except ValidationError as e:
        pytest.fail(f"Error response validation failed: {e}")


def test_runtime_guard_friendly_error_messages():
    """Test that runtime guards provide friendly error messages."""
    agent = DefaultTakeoffAgent()
    
    # Test with invalid request type
    with pytest.raises(ValueError) as exc_info:
        agent.run("not_a_request")  # type: ignore
    
    error_msg = str(exc_info.value)
    assert "Invalid TakeoffRequest" in error_msg
    assert "friendly" in error_msg.lower() or "clear" in error_msg.lower() or "validation" in error_msg.lower()


def test_runtime_guard_early_failure():
    """Test that runtime guards fail early with clear messages."""
    agent = DefaultTakeoffAgent()
    
    # Test with completely invalid input
    with pytest.raises(ValueError) as exc_info:
        agent.run(None)  # type: ignore
    
    error_msg = str(exc_info.value)
    assert "Invalid TakeoffRequest" in error_msg
    # Should fail early, not after processing
    assert "Takeoff failed" not in error_msg
