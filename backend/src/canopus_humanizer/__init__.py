"""canopus-humanizer: Deterministic text humanization and transformation engine."""

from canopus_humanizer.engine.models import (
    Change,
    DocumentBlock,
    DocumentModel,
    ProtectedSpan,
    TransformRequest,
    TransformResult,
    ValidationIssue,
)
from canopus_humanizer.engine.errors import (
    CanopusError,
    InputError,
    FormatError,
    RulesetError,
    ProtectionError,
    ValidationError,
    SecurityError,
    ResourceError,
)
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.rules.schema import RuleDefinition, RulesetDefinition

__version__ = "2.6.0"

__all__ = [
    "__version__",
    "Pipeline",
    "TransformRequest",
    "TransformResult",
    "Change",
    "ValidationIssue",
    "ProtectedSpan",
    "DocumentBlock",
    "DocumentModel",
    "RuleRegistry",
    "RuleDefinition",
    "RulesetDefinition",
    "CanopusError",
    "InputError",
    "FormatError",
    "RulesetError",
    "ProtectionError",
    "ValidationError",
    "SecurityError",
    "ResourceError",
]
