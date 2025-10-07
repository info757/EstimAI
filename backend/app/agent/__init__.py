"""EstimAI Agent System

This package provides the core agent functionality for the EstimAI system.
The agent is responsible for processing PDF files and extracting construction
takeoff data using computer vision and LLM techniques.

Key Components:
- types: Stable, versioned data structures
- protocols: Interface definitions for agent implementations
- takeoff: Main agent implementation
- errors: Agent-specific error handling

The agent contract is locked in types.py and protocols.py to prevent
breaking changes and ensure stable API evolution.
"""
from .protocols import (
    AGENT_PROTOCOL_DATE,
    AGENT_PROTOCOL_VERSION,
    AgentError,
    TakeoffAgent,
)
from .types import (
    AGENT_CONTRACT_DATE,
    AGENT_CONTRACT_VERSION,
    AgentSummary,
    PipelineInfo,
    ProposedReview,
    TakeoffOptions,
    TakeoffRequest,
    TakeoffResponse,
)

__all__ = [
    # Types
    "TakeoffRequest",
    "TakeoffResponse",
    "TakeoffOptions",
    "ProposedReview",
    "AgentSummary",
    "PipelineInfo",
    # Protocols
    "TakeoffAgent",
    "AgentError",
    # Version info
    "AGENT_CONTRACT_VERSION",
    "AGENT_CONTRACT_DATE",
    "AGENT_PROTOCOL_VERSION",
    "AGENT_PROTOCOL_DATE",
]
