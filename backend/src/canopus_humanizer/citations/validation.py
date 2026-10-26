"""Citation metadata validation and provenance verification status."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


VerificationStatus = Literal["formatted", "metadata_checked", "not_verified", "invalid"]


@dataclass(frozen=True)
class CitationMetadata:
    """Strongly-typed citation reference metadata."""
    title: str
    authors: Tuple[str, ...]
    year: str
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    status: VerificationStatus = "not_verified"
    validation_notes: Tuple[str, ...] = field(default_factory=tuple)


class CitationValidator:
    """Validates citation metadata completeness, identifier syntax, and records verification state."""

    @staticmethod
    def validate_doi(doi: str) -> bool:
        """Validates DOI string format e.g. 10.1000/182."""
        if not doi:
            return False
        clean = doi.strip()
        if clean.startswith("https://doi.org/"):
            clean = clean[16:]
        elif clean.startswith("http://doi.org/"):
            clean = clean[15:]
        elif clean.startswith("doi:"):
            clean = clean[4:]
        return bool(re.match(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$", clean))

    def validate_metadata(self, data: Dict[str, Any]) -> CitationMetadata:
        """Validates reference metadata dictionary and returns a typed CitationMetadata object."""
        notes = []

        title = str(data.get("title", "")).strip()
        if not title:
            notes.append("Missing required field: 'title'")

        raw_authors = data.get("authors", [])
        if isinstance(raw_authors, str):
            authors = tuple([raw_authors.strip()]) if raw_authors.strip() else ()
        elif isinstance(raw_authors, list):
            authors = tuple([str(a).strip() for a in raw_authors if str(a).strip()])
        else:
            authors = ()

        if not authors:
            notes.append("Missing required field: 'authors'")

        year = str(data.get("year", "")).strip()
        if not year:
            notes.append("Missing required field: 'year'")
        elif not re.match(r"^\d{4}[a-z]?$", year):
            notes.append(f"Unusual year format: '{year}'")

        doi = str(data.get("doi", "")).strip()
        if doi and not self.validate_doi(doi):
            notes.append(f"Invalid DOI format: '{doi}'")

        venue = str(data.get("venue") or data.get("journal", "")).strip()
        volume = str(data.get("volume", "")).strip()
        issue = str(data.get("issue") or data.get("number", "")).strip()
        pages = str(data.get("pages", "")).strip()

        if any("Missing required field" in n for n in notes):
            status: VerificationStatus = "invalid"
        elif doi and self.validate_doi(doi):
            status = "metadata_checked"
        else:
            status = "formatted"

        # Explicitly declare external verification status
        notes.append("External repository verification: not_verified (offline engine)")

        return CitationMetadata(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            status=status,
            validation_notes=tuple(notes),
        )
