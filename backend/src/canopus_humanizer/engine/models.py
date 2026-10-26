"""Core data models and contracts for Canopus Humanizer engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


@dataclass(frozen=True)
class ProtectedSpan:
    """Represents a segment of text shielded from any modifications."""
    span_id: str
    start: int
    end: int
    kind: str
    original: str
    detector: str
    confidence: float = 1.0


@dataclass(frozen=True)
class Change:
    """Represents a specific proposed or applied transformation."""
    rule_id: str
    start: int
    end: int
    before: str
    after: str
    category: str
    requires_review: bool


@dataclass(frozen=True)
class ValidationIssue:
    """Represents an issue discovered during post-transform validation."""
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class TransformRequest:
    """Request contract specifying text and configuration for transformation."""
    text: str
    mode: Literal["conservative", "standard", "manual_review"] = "conservative"
    ruleset_ids: Tuple[str, ...] = ("base",)
    language: str = "en"
    preserve_citations: bool = True
    preserve_numbers: bool = True
    preserve_code: bool = True
    seed: int = 0
    max_changes: int = 500
    custom_protected_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TransformResult:
    """Complete result contract returned from transformation pipeline."""
    original_text: str
    transformed_text: str
    changes: Tuple[Change, ...]
    issues: Tuple[ValidationIssue, ...]
    engine_version: str
    ruleset_versions: Tuple[str, ...]
    accepted: bool
    diff: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentBlock:
    """A structural segment of a document (e.g. paragraph, header, table cell)."""
    block_id: str
    block_type: str
    start: int
    end: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentModel:
    """Structured representation of a parsed document."""
    blocks: Tuple[DocumentBlock, ...]
    format_name: str
    source_metadata: Dict[str, Any] = field(default_factory=dict)
