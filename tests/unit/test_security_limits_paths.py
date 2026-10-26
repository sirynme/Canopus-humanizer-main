"""Unit tests for resource limits, ReDoS pattern validation, and path traversal defenses."""

import pytest
from pathlib import Path

from canopus_humanizer.engine.errors import InputError, ResourceError, SecurityError
from canopus_humanizer.security.limits import (
    ResourceLimits,
    validate_input_limits,
    validate_regex_pattern,
)
from canopus_humanizer.security.paths import safe_join, validate_filename


def test_validate_input_limits_success():
    limits = ResourceLimits(max_input_bytes=1000, max_input_chars=200)
    # Valid input within bounds
    validate_input_limits("Valid sample input under limits.", limits=limits)


def test_validate_input_limits_char_exceeded():
    limits = ResourceLimits(max_input_chars=10)
    with pytest.raises(ResourceError) as exc_info:
        validate_input_limits("This string exceeds 10 chars", limits=limits)
    assert exc_info.value.code == "INPUT_TOO_LARGE"


def test_validate_input_limits_byte_exceeded():
    limits = ResourceLimits(max_input_bytes=10, max_input_chars=100)
    with pytest.raises(ResourceError) as exc_info:
        validate_input_limits("Exceeds 10 bytes easily", limits=limits)
    assert exc_info.value.code == "INPUT_TOO_LARGE"


def test_validate_input_type_error():
    with pytest.raises(InputError):
        validate_input_limits(12345)


def test_validate_regex_pattern_safe():
    compiled = validate_regex_pattern(r"\btest\b")
    assert compiled.pattern == r"\btest\b"


def test_validate_regex_pattern_length_limit():
    limits = ResourceLimits(max_regex_pattern_length=20)
    with pytest.raises(SecurityError) as exc_info:
        validate_regex_pattern("a" * 25, limits=limits)
    assert exc_info.value.code == "REGEX_TOO_COMPLEX"


def test_validate_regex_pattern_catastrophic_backtracking():
    with pytest.raises(SecurityError) as exc_info:
        validate_regex_pattern(r"([a-z]+)+")
    assert exc_info.value.code == "REGEX_UNSAFE"


def test_validate_filename_traversal():
    with pytest.raises(SecurityError) as exc_info:
        validate_filename("../etc/passwd")
    assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    with pytest.raises(SecurityError) as exc_info:
        validate_filename("/absolute/path")
    assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    with pytest.raises(SecurityError) as exc_info:
        validate_filename("C:\\Windows\\System32")
    assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    with pytest.raises(SecurityError) as exc_info:
        validate_filename("filename\x00with_nul")
    assert exc_info.value.code == "NUL_BYTE_DETECTED"


def test_safe_join_within_bounds(tmp_path):
    sub = safe_join(tmp_path, "subfolder", "file.txt")
    assert sub == (tmp_path / "subfolder" / "file.txt").resolve()


def test_safe_join_traversal_rejection(tmp_path):
    with pytest.raises(SecurityError):
        safe_join(tmp_path, "..", "secret.txt")
