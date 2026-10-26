"""Safe path operations and traversal defenses."""

import os
import re
from pathlib import Path
from typing import Union

from canopus_humanizer.engine.errors import SecurityError, PATH_TRAVERSAL_DETECTED


def validate_filename(filename: str) -> str:
    """Validates and cleanses a filename to prevent traversal and invalid path characters."""
    if not filename or not filename.strip():
        raise SecurityError("Filename cannot be empty", code="INVALID_FILENAME")

    if "\x00" in filename:
        raise SecurityError("Filename cannot contain null bytes", code="NUL_BYTE_DETECTED")

    # Reject traversal tokens
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise SecurityError(
            f"Path traversal characters detected in filename: '{filename}'",
            code=PATH_TRAVERSAL_DETECTED,
        )

    # Reject Windows drive indicators e.g. C:
    if re.match(r"^[a-zA-Z]:", filename):
        raise SecurityError(
            f"Drive prefix detected in filename: '{filename}'",
            code=PATH_TRAVERSAL_DETECTED,
        )

    # Disallow absolute paths
    p = Path(filename)
    if p.is_absolute():
        raise SecurityError(
            f"Absolute path not permitted: '{filename}'",
            code=PATH_TRAVERSAL_DETECTED,
        )

    return filename.strip()


def safe_join(base_dir: Union[str, Path], *paths: str) -> Path:
    """Safely joins paths ensuring the target strictly resides inside base_dir."""
    base_path = Path(base_dir).resolve()

    for segment in paths:
        validate_filename(segment)

    target_path = base_path.joinpath(*paths).resolve()

    # Guard: target must be within base_path
    try:
        target_path.relative_to(base_path)
    except ValueError:
        raise SecurityError(
            f"Path traversal detected: target '{target_path}' escapes base '{base_path}'",
            code=PATH_TRAVERSAL_DETECTED,
        )

    return target_path
