"""Secure ZIP/DOCX archive handling with ZIP-bomb and path-traversal safeguards."""

import io
import zipfile
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple, Union

from canopus_humanizer.engine.errors import SecurityError, FormatError, ARCHIVE_BOMB_DETECTED, PATH_TRAVERSAL_DETECTED
from canopus_humanizer.security.limits import DEFAULT_LIMITS, ResourceLimits
from canopus_humanizer.security.paths import validate_filename


ZIP_MAGIC_BYTES = b"PK\x03\x04"


class SafeArchiveHandler:
    """Safely inspects, validates, and manipulates ZIP archives (including DOCX)."""

    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or DEFAULT_LIMITS

    def validate_archive_bytes(self, data: bytes) -> zipfile.ZipFile:
        """Validates that bytes represent a safe, well-formed ZIP file."""
        if not data.startswith(ZIP_MAGIC_BYTES):
            raise FormatError("Data is not a valid ZIP archive (missing PK magic bytes)", code="INVALID_ARCHIVE")

        bio = io.BytesIO(data)
        try:
            zf = zipfile.ZipFile(bio, "r")
        except zipfile.BadZipFile as e:
            raise FormatError(f"Malformed ZIP archive: {e}", code="MALFORMED_ARCHIVE")

        self.inspect_zip(zf)
        return zf

    def inspect_zip(self, zf: zipfile.ZipFile) -> None:
        """Inspects all entries in a ZipFile against zip-bomb and path traversal vulnerabilities."""
        infolist = zf.infolist()

        if len(infolist) > self.limits.max_archive_entries:
            raise SecurityError(
                f"Archive entry count ({len(infolist)}) exceeds limit ({self.limits.max_archive_entries})",
                code=ARCHIVE_BOMB_DETECTED,
            )

        total_uncompressed_bytes = 0
        total_compressed_bytes = 0
        seen_filenames = set()

        for info in infolist:
            filename = info.filename
            # Path traversal check on every entry
            if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
                raise SecurityError(
                    f"Path traversal detected in archive entry: '{filename}'",
                    code=PATH_TRAVERSAL_DETECTED,
                )

            # Duplicate filename ambiguity check
            norm_name = filename.strip().lower()
            if norm_name in seen_filenames:
                raise SecurityError(
                    f"Ambiguous archive with duplicate entry: '{filename}'",
                    code="ARCHIVE_DUPLICATE_ENTRY",
                )
            seen_filenames.add(norm_name)

            # Size accumulation
            total_uncompressed_bytes += info.file_size
            total_compressed_bytes += info.compress_size

            if total_uncompressed_bytes > self.limits.max_decompressed_bytes:
                raise SecurityError(
                    f"Archive decompressed size ({total_uncompressed_bytes} bytes) exceeds limit ({self.limits.max_decompressed_bytes} bytes)",
                    code=ARCHIVE_BOMB_DETECTED,
                )

            # Per-entry compression ratio check for files > 10KB
            if info.compress_size > 0 and info.file_size > 10_000:
                ratio = info.file_size / info.compress_size
                if ratio > 100.0:
                    raise SecurityError(
                        f"Excessive per-file compression ratio ({ratio:.1f}x) in '{filename}'",
                        code=ARCHIVE_BOMB_DETECTED,
                    )

        # Overall compression ratio check
        if total_compressed_bytes > 0:
            overall_ratio = total_uncompressed_bytes / total_compressed_bytes
            if overall_ratio > self.limits.max_decompression_ratio and total_uncompressed_bytes > 1_000_000:
                raise SecurityError(
                    f"Archive overall compression ratio ({overall_ratio:.1f}x) exceeds limit ({self.limits.max_decompression_ratio}x)",
                    code=ARCHIVE_BOMB_DETECTED,
                )
