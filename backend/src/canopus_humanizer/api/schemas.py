"""Pydantic schemas for canopus-humanizer and Canopus API."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class HumanizeRequest(BaseModel):
    """Request schema for legacy /v1/humanize endpoint."""
    text: str = Field(..., min_length=1, max_length=50000, description="Input text to process")
    intensity: Optional[float] = Field(70.0, ge=10.0, le=100.0, description="Transformation intensity percentage")
    style: Optional[str] = Field("academic", description="Writing register (academic, conversational, technical)")
    protected_terms: Optional[List[str]] = Field(default_factory=list, description="Terms to preserve unchanged")
    seed: Optional[int] = Field(None, description="Optional integer seed for deterministic output")

    # Optional stage overrides
    enable_synonyms: Optional[bool] = Field(True)
    enable_phrase_rewrite: Optional[bool] = Field(True)
    enable_determiner_swap: Optional[bool] = Field(True)
    enable_discourse_rotate: Optional[bool] = Field(True)
    enable_sentence_fusion: Optional[bool] = Field(True)


class HumanizeResponse(BaseModel):
    """Response schema for legacy /v1/humanize endpoint."""
    success: bool
    humanized_text: str
    words_processed: int
    modifications_count: int
    latency_ms: float
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Response schema for service health status."""
    status: str
    engine: str
    version: str
    timestamp: float


class TransformChangeSchema(BaseModel):
    """Schema for individual recorded transformation."""
    rule_id: str
    start: int
    end: int
    before: str
    after: str
    category: str
    requires_review: bool


class ValidationIssueSchema(BaseModel):
    """Schema for individual validation issue."""
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    start: Optional[int] = None
    end: Optional[int] = None


class TransformApiRequest(BaseModel):
    """Complete Canopus transformation request schema."""
    text: str = Field(..., min_length=1, max_length=500000, description="Input text to process")
    mode: Literal["conservative", "standard", "manual_review"] = "conservative"
    ruleset_ids: List[str] = Field(default_factory=lambda: ["base"], description="List of ruleset IDs to apply")
    custom_protected_terms: List[str] = Field(default_factory=list, description="Terms that must remain unchanged")
    max_changes: int = Field(500, ge=1, le=5000, description="Maximum permitted mutations")
    preserve_citations: bool = Field(True)
    preserve_numbers: bool = Field(True)
    no_op: bool = Field(False, description="Execute in no-op validation mode without mutating text")


class TransformApiResponse(BaseModel):
    """Complete Canopus transformation response schema."""
    accepted: bool
    original_text: str
    transformed_text: str
    changes: List[TransformChangeSchema]
    issues: List[ValidationIssueSchema]
    engine_version: str
    ruleset_versions: List[str]
    diff: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)


class CitationFormatRequest(BaseModel):
    """Request schema for citation formatting."""
    title: str
    authors: List[str]
    year: str
    venue: Optional[str] = ""
    volume: Optional[str] = ""
    issue: Optional[str] = ""
    pages: Optional[str] = ""
    doi: Optional[str] = ""


class CitationFormatResponse(BaseModel):
    """Response schema for formatted citations and validation status."""
    apa: str
    ieee: str
    bibtex: str
    status: str
    validation_notes: List[str]


class ErrorResponse(BaseModel):
    """Standardized error envelope for API domain exceptions."""
    error: str = Field(..., description="Exception class name (e.g. InputError, RulesetError)")
    code: str = Field(..., description="Machine-readable standardized error code")
    message: str = Field(..., description="Safe human-readable error description")
    detail: str = Field(..., description="Standard detail field for client compatibility")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional structured error metadata")
