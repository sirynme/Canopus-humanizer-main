"""Error definitions and hierarchy for Canopus Humanizer engine."""

from typing import Optional


class CanopusError(Exception):
    """Base exception class for all Canopus Humanizer errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InputError(CanopusError):
    """Raised when input text, parameters, or encodings are invalid."""
    pass


class FormatError(CanopusError):
    """Raised when document format parsing or serialization fails."""
    pass


class RulesetError(CanopusError):
    """Raised when rule files are invalid, malformed, or conflicting."""
    pass


class ProtectionError(CanopusError):
    """Raised when protected span detection, shielding, or restoration fails."""
    pass


class ValidationError(CanopusError):
    """Raised when output validation or semantic preservation checks fail."""
    pass


class SecurityError(CanopusError):
    """Raised when a security boundary is violated (e.g. archive bomb, path traversal)."""
    pass


class ResourceError(CanopusError):
    """Raised when configured resource limits (size, count, time) are exceeded."""
    pass


# Stable error code constants
INPUT_INVALID = "INPUT_INVALID"
INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
NUL_BYTE_DETECTED = "NUL_BYTE_DETECTED"
UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
PARSER_FAILED = "PARSER_FAILED"
RULESET_INVALID = "RULESET_INVALID"
RULE_CONFLICT = "RULE_CONFLICT"
RULE_NOT_FOUND = "RULE_NOT_FOUND"
PROTECTED_SPAN_MISMATCH = "PROTECTED_SPAN_MISMATCH"
PLACEHOLDER_CORRUPTED = "PLACEHOLDER_CORRUPTED"
OUTPUT_VALIDATION_FAILED = "OUTPUT_VALIDATION_FAILED"
SEMANTIC_DRIFT_DETECTED = "SEMANTIC_DRIFT_DETECTED"
NEGATION_ALTERED = "NEGATION_ALTERED"
SECURITY_VIOLATION = "SECURITY_VIOLATION"
ARCHIVE_BOMB_DETECTED = "ARCHIVE_BOMB_DETECTED"
PATH_TRAVERSAL_DETECTED = "PATH_TRAVERSAL_DETECTED"
RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
SERIALIZATION_FAILED = "SERIALIZATION_FAILED"
CITATION_UNVERIFIED = "CITATION_UNVERIFIED"
