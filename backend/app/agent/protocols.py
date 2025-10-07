"""Protocol definitions for the EstimAI agent system.

This module defines the interfaces that agent implementations must satisfy.
Using protocols allows for:

1. **Flexible Implementation**: Multiple agent implementations can exist
2. **Type Safety**: Full type checking without tight coupling
3. **Testing**: Easy mocking and testing of agent behavior
4. **Evolution**: Protocol can evolve while maintaining compatibility

The agent contract is locked here - any changes to these protocols
should be carefully considered and versioned.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import TakeoffRequest, TakeoffResponse


@runtime_checkable
class TakeoffAgent(Protocol):
    """Protocol for takeoff agents.
    
    This protocol defines the interface that all takeoff agent
    implementations must satisfy. The agent is responsible for:
    
    1. Processing PDF files and extracting construction data
    2. Detecting utility networks (storm, sanitary, water)
    3. Calculating pipe depths and trench volumes
    4. Generating quality assurance flags
    5. Returning structured data in the expected format
    
    The agent should be idempotent - multiple calls with the same
    inputs should produce the same outputs (within reason).
    """

    def run(self, req: TakeoffRequest) -> TakeoffResponse:
        """Run the takeoff agent on the provided request.
        
        Args:
            req: The takeoff request containing session_id, file data, and options
            
        Returns:
            TakeoffResponse containing the proposed review, summary, and any warnings
            
        Raises:
            AgentError: If the agent encounters an unrecoverable error

        """
        ...


class AgentError(Exception):
    """Base exception for agent-specific errors.
    
    Agent implementations should raise errors that inherit from this class
    to provide structured error information to the calling code.
    """

    def __init__(self, message: str, error_code: str = "AGENT_ERROR", retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable

    def get_error_code(self) -> str:
        """Get a machine-readable error code."""
        return self.error_code

    def get_error_message(self) -> str:
        """Get a human-readable error message."""
        return str(self)

    def is_retryable(self) -> bool:
        """Whether this error is retryable."""
        return self.retryable


# Version information for the agent protocols
AGENT_PROTOCOL_VERSION = "1.0.0"
AGENT_PROTOCOL_DATE = "2025-10-06"
