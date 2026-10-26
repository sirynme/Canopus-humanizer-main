"""Security tests verifying defense against malicious inputs, traversal, and resource exhaustion."""

import io
import zipfile
import pytest

from canopus_humanizer.engine.errors import InputError, ResourceError, SecurityError
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.security.archive import SafeArchiveHandler
from canopus_humanizer.security.limits import ResourceLimits, validate_input_limits, validate_regex_pattern
from canopus_humanizer.security.paths import safe_join, validate_filename


def test_defense_nul_byte_injection():
    pipeline = Pipeline()
    req = TransformRequest(text="Malicious string \x00 with embedded NUL byte.")
    with pytest.raises(InputError) as exc_info:
        pipeline.process(req)
    assert exc_info.value.code == "NUL_BYTE_DETECTED"


def test_defense_oversized_text_payload():
    pipeline = Pipeline(limits=ResourceLimits(max_input_bytes=1000, max_input_chars=200))
    huge_text = "A" * 5000
    req = TransformRequest(text=huge_text)
    with pytest.raises(ResourceError) as exc_info:
        pipeline.process(req)
    assert exc_info.value.code == "INPUT_TOO_LARGE"


def test_defense_zip_bomb_compression_ratio():
    """Generates an in-memory high compression ratio zip bomb and verifies rejection."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1MB of zeroes compresses to very few bytes
        zf.writestr("zeroes.bin", b"\x00" * 2_000_000)
    zip_bytes = buf.getvalue()

    handler = SafeArchiveHandler(limits=ResourceLimits(max_decompression_ratio=5.0))
    with pytest.raises(SecurityError) as exc_info:
        handler.validate_archive_bytes(zip_bytes)
    assert exc_info.value.code == "ARCHIVE_BOMB_DETECTED"


def test_defense_path_traversal_filenames():
    traversal_vectors = [
        "../../etc/shadow",
        "..\\..\\Windows\\System32",
        "/usr/local/bin/malicious",
        "C:\\autoexec.bat",
        "file\x00.txt",
    ]
    for vector in traversal_vectors:
        with pytest.raises(SecurityError):
            validate_filename(vector)


def test_defense_catastrophic_backtracking_regex():
    with pytest.raises(SecurityError) as exc_info:
        validate_regex_pattern(r"(a+)+$")
    assert exc_info.value.code == "REGEX_UNSAFE"
