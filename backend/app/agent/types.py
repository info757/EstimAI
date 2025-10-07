"""Stable, versioned types for the EstimAI agent system.

This module defines the core data structures that the agent system uses
for communication between components. These types are designed to be:

1. **Stable**: Changes should be additive, not breaking
2. **Versioned**: Clear evolution path for future changes
3. **Typed**: Full type safety with Pydantic validation
4. **Documented**: Clear field descriptions and examples

The agent contract is locked here - any changes to these types
should be carefully considered and versioned.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TakeoffOptions(BaseModel):
    """Configuration options for the takeoff agent.
    
    These options control how the agent processes PDFs and generates
    takeoff results. All options have sensible defaults.
    """

    dry_run: bool = Field(
        default=False,
        description="If True, run analysis but don't commit results"
    )
    max_pages: int | None = Field(
        default=None,
        description="Maximum number of pages to process (None = all pages)"
    )
    force_ground_source: Literal["profile", "surface", "constant"] | None = Field(
        default=None,
        description="Force specific ground elevation source (None = auto-detect)"
    )


class TakeoffRequest(BaseModel):
    """Request to the takeoff agent.
    
    This is the stable input contract for the agent system.
    Either file_ref OR upload_file must be provided, but not both.
    """

    session_id: str = Field(
        description="Unique session identifier for this takeoff request"
    )
    file_ref: str | None = Field(
        default=None,
        description="Reference to an existing file (mutually exclusive with upload_file)"
    )
    upload_file: bytes | None = Field(
        default=None,
        description="Raw PDF file bytes (mutually exclusive with file_ref)"
    )
    options: TakeoffOptions = Field(
        default_factory=TakeoffOptions,
        description="Configuration options for the takeoff process"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that exactly one of file_ref or upload_file is provided."""
        if not self.file_ref and not self.upload_file:
            raise ValueError("Either file_ref or upload_file must be provided")
        if self.file_ref and self.upload_file:
            raise ValueError("Cannot provide both file_ref and upload_file")


class ProposedReview(BaseModel):
    """A proposed review that can be committed to the database.
    
    This contains the structured takeoff data that will be processed
    by the review system and converted to count items.
    """

    payload: dict[str, Any] = Field(
        description="The structured takeoff data (EstimAIResult format)"
    )


class PipelineInfo(BaseModel):
    """Information about the pipeline components used in the takeoff.
    
    This provides transparency about which technologies and methods
    were used to generate the takeoff results.
    """
    
    apryse_enabled: bool = Field(
        description="Whether Apryse PDFNet was used for vector extraction"
    )
    llm_enabled: bool = Field(
        description="Whether LLM was used for detection/analysis"
    )
    llm_model: str | None = Field(
        default=None,
        description="Name of the LLM model used (e.g., 'gpt-4o-mini')"
    )
    ground_source: Literal["profile", "surface", "constant", "unknown"] | None = Field(
        default=None,
        description="Primary source used for ground elevation data"
    )
    prompt_token_count: int | None = Field(
        default=None,
        description="Approximate token count of prompts sent to LLM"
    )
    completion_token_count: int | None = Field(
        default=None,
        description="Approximate token count of LLM responses"
    )


class AgentSummary(BaseModel):
    """Summary statistics from the agent run.
    
    This provides high-level metrics about what the agent found
    and any quality assurance flags that were raised.
    """

    pipes_total: int = Field(
        description="Total number of pipes detected across all networks"
    )
    qa_flags: dict[str, int] = Field(
        default_factory=dict,
        description="Quality assurance flags and their counts"
    )
    pipeline: PipelineInfo | None = Field(
        default=None,
        description="Information about pipeline components used"
    )


class TakeoffResponse(BaseModel):
    """Response from the takeoff agent.
    
    This is the stable output contract for the agent system.
    Contains the proposed review, summary statistics, and any warnings.
    """

    proposed_review: ProposedReview | None = Field(
        default=None,
        description="The proposed review (None if agent failed)"
    )
    summary: AgentSummary = Field(
        description="Summary statistics from the agent run"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages from the agent run"
    )
    error: str | None = Field(
        default=None,
        description="Error message if the agent failed"
    )


# Version information for the agent contract
AGENT_CONTRACT_VERSION = "1.0.0"
AGENT_CONTRACT_DATE = "2025-10-06"
