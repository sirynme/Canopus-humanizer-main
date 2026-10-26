"""Canopus core engine components."""

from canopus_humanizer.engine.models import (
    Change,
    DocumentBlock,
    DocumentModel,
    ProtectedSpan,
    TransformRequest,
    TransformResult,
    ValidationIssue,
)
from canopus_humanizer.engine.errors import CanopusError
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.engine.planner import ChangePlanner
from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector, ProtectedSpanRegistry
from canopus_humanizer.engine.segmentation import TextSegmenter
from canopus_humanizer.engine.transforms import apply_changes_to_text
from canopus_humanizer.engine.validation import OutputValidator
from canopus_humanizer.engine.diff import generate_unified_diff

__all__ = [
    "Pipeline",
    "TransformRequest",
    "TransformResult",
    "Change",
    "ValidationIssue",
    "ProtectedSpan",
    "DocumentBlock",
    "DocumentModel",
    "CanopusError",
    "ChangePlanner",
    "ProtectedSpanDetector",
    "ProtectedSpanRegistry",
    "TextSegmenter",
    "apply_changes_to_text",
    "OutputValidator",
    "generate_unified_diff",
]
