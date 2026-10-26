"""Resource limits and complexity bounds for Canopus Humanizer."""

import re
from dataclasses import dataclass
from typing import Optional

from canopus_humanizer.engine.errors import InputError, ResourceError, SecurityError, INPUT_TOO_LARGE, RESOURCE_LIMIT_EXCEEDED


@dataclass(frozen=True)
class ResourceLimits:
    """Configurable security and performance boundaries."""
    max_input_bytes: int = 5_000_000         # 5 MB max text payload
    max_input_chars: int = 1_000_000         # 1M characters
    max_archive_entries: int = 500           # Max files in zip/docx
    max_decompressed_bytes: int = 25_000_000 # 25 MB max total decompressed
    max_decompression_ratio: float = 10.0    # Max allowed compression ratio (bomb protection)
    max_nesting_depth: int = 20
    max_changes: int = 500                   # Max mutations per request
    max_regex_pattern_length: int = 300      # Max regex length to prevent ReDoS
    max_execution_time_seconds: float = 30.0 # Time limit for processing


DEFAULT_LIMITS = ResourceLimits()


def validate_input_limits(text: str, limits: Optional[ResourceLimits] = None) -> None:
    """Validates that input text satisfies byte and character limits."""
    lim = limits or DEFAULT_LIMITS
    if not isinstance(text, str):
        raise InputError("Input text must be a string", code="INPUT_INVALID")

    char_count = len(text)
    if char_count > lim.max_input_chars:
        raise ResourceError(
            f"Input text length ({char_count} chars) exceeds maximum allowed {lim.max_input_chars}",
            code=INPUT_TOO_LARGE,
            details={"chars": char_count, "max_chars": lim.max_input_chars},
        )

    byte_count = len(text.encode("utf-8", errors="replace"))
    if byte_count > lim.max_input_bytes:
        raise ResourceError(
            f"Input byte size ({byte_count} bytes) exceeds maximum allowed {lim.max_input_bytes}",
            code=INPUT_TOO_LARGE,
            details={"bytes": byte_count, "max_bytes": lim.max_input_bytes},
        )


def validate_regex_pattern(pattern: str, limits: Optional[ResourceLimits] = None) -> re.Pattern:
    """Validates regex pattern length and compiles safely, guarding against obvious catastrophic backtracking."""
    lim = limits or DEFAULT_LIMITS
    if len(pattern) > lim.max_regex_pattern_length:
        raise SecurityError(
            f"Regex pattern exceeds maximum length ({len(pattern)} > {lim.max_regex_pattern_length})",
            code="REGEX_TOO_COMPLEX",
        )

    # Check for obvious catastrophic backtracking patterns e.g. (a+)+ or (.*)*
    dangerous_constructs = [
        r"\([^)]*[\*\+][^)]*\)[\*\+]",  # nested quantifiers like (a+)+
        r"\(\.\*[\*\+]\)",               # (.*)*
    ]
    for dc in dangerous_constructs:
        if re.search(dc, pattern):
            raise SecurityError(
                f"Potentially catastrophic backtracking pattern detected: {pattern}",
                code="REGEX_UNSAFE",
            )

    try:
        return re.compile(pattern)
    except re.error as e:
        raise SecurityError(f"Invalid regular expression '{pattern}': {e}", code="REGEX_INVALID")
