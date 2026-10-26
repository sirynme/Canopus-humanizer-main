"""Stage 1: Input validation and text normalization for Canopus Humanizer engine."""

import re
import unicodedata
from typing import Optional

from canopus_humanizer.engine.errors import InputError, NUL_BYTE_DETECTED
from canopus_humanizer.security.limits import DEFAULT_LIMITS, ResourceLimits, validate_input_limits


# Invisible control characters to strip (zero-width spaces, bidi overrides)
# Explicitly preserves standard whitespace: space, \t, \n, \r
DISALLOWED_CONTROL_CHARS_PATTERN = re.compile(
    r"[\u200B-\u200D\uFEFF\u202A-\u202E\u2066-\u2069\x01-\x08\x0B\x0C\x0E-\x1F\x7F]"
)


def normalize_input_text(
    text: str,
    limits: Optional[ResourceLimits] = None,
) -> str:
    """
    Stage 1: Validates and normalizes input text.
    1. Enforces resource limits (character count, line count).
    2. Strictly rejects prohibited NUL bytes (0x00).
    3. Normalizes Unicode into canonical composed form (NFC).
    4. Removes invisible/deceptive control characters while preserving formatting whitespace.
    """
    if text is None:
        raise InputError("Input text cannot be None")

    res_limits = limits or DEFAULT_LIMITS
    validate_input_limits(text, res_limits)

    if "\x00" in text:
        raise InputError("Input text contains prohibited NUL bytes", code=NUL_BYTE_DETECTED)

    # Unicode normalization to canonical composed form (NFC)
    normalized = unicodedata.normalize("NFC", text)

    # Strip invisible zero-width and deceptive bidi control characters
    cleaned = DISALLOWED_CONTROL_CHARS_PATTERN.sub("", normalized)

    return cleaned
