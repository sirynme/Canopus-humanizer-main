"""Unit tests for safe ZIP and DOCX archive handling."""

import io
import zipfile
import pytest

from canopus_humanizer.engine.errors import FormatError, SecurityError
from canopus_humanizer.security.archive import SafeArchiveHandler
from canopus_humanizer.security.limits import ResourceLimits


def create_zip_bytes(entries):
    """Helper to generate in-memory ZIP archives."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_archive_valid_bytes():
    handler = SafeArchiveHandler()
    zip_bytes = create_zip_bytes({"test.txt": b"Hello world"})
    zf = handler.validate_archive_bytes(zip_bytes)
    assert len(zf.namelist()) == 1


def test_archive_non_zip_rejected():
    handler = SafeArchiveHandler()
    with pytest.raises(FormatError) as exc_info:
        handler.validate_archive_bytes(b"Not a zip archive at all")
    assert exc_info.value.code == "INVALID_ARCHIVE"


def test_archive_entry_count_limit():
    handler = SafeArchiveHandler(limits=ResourceLimits(max_archive_entries=5))
    many_entries = {f"file_{i}.txt": b"content" for i in range(10)}
    zip_bytes = create_zip_bytes(many_entries)

    with pytest.raises(SecurityError) as exc_info:
        handler.validate_archive_bytes(zip_bytes)
    assert exc_info.value.code == "ARCHIVE_BOMB_DETECTED"


def test_archive_decompressed_size_limit():
    handler = SafeArchiveHandler(limits=ResourceLimits(max_decompressed_bytes=500))
    large_entry = {"large.txt": b"A" * 1000}
    zip_bytes = create_zip_bytes(large_entry)

    with pytest.raises(SecurityError) as exc_info:
        handler.validate_archive_bytes(zip_bytes)
    assert exc_info.value.code == "ARCHIVE_BOMB_DETECTED"


def test_archive_path_traversal_entry():
    handler = SafeArchiveHandler()
    traversal_entry = {"../../etc/passwd": b"root:x:0:0:..."}
    zip_bytes = create_zip_bytes(traversal_entry)

    with pytest.raises(SecurityError) as exc_info:
        handler.validate_archive_bytes(zip_bytes)
    assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"
