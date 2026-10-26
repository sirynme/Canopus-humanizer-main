"""Unit tests for citation formatting and validation."""

import pytest
from canopus_humanizer.citations.formatters import CitationFormatter
from canopus_humanizer.citations.validation import CitationValidator


def test_apa_formatting():
    meta = {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": ["He, K.", "Zhang, X.", "Ren, S.", "Sun, J."],
        "year": "2016",
        "venue": "CVPR",
        "pages": "770-778",
        "doi": "10.1109/CVPR.2016.90",
    }
    apa = CitationFormatter.format_apa(meta)
    assert "He, K., Zhang, X., Ren, S., & Sun, J. (2016)." in apa
    assert "Deep Residual Learning for Image Recognition." in apa
    assert "CVPR, 770-778." in apa
    assert "https://doi.org/10.1109/CVPR.2016.90" in apa


def test_bibtex_formatting_escapes_special_characters():
    meta = {
        "key": "he2016",
        "title": "Algorithms & Systems: 95% Speedup",
        "authors": ["He, K."],
        "journal": "Nature & Science",
        "year": "2016",
    }
    bib = CitationFormatter.format_bibtex(meta)
    assert r"Algorithms \& Systems: 95\% Speedup" in bib
    assert r"Nature \& Science" in bib


def test_citation_validator_doi_and_status():
    validator = CitationValidator()

    # Valid DOI
    meta = validator.validate_metadata({
        "title": "Paper Title",
        "authors": ["Author, A."],
        "year": "2024",
        "doi": "10.1000/182",
    })
    assert meta.status == "metadata_checked"
    assert "External repository verification: not_verified" in meta.validation_notes[0]

    # Missing author
    bad_meta = validator.validate_metadata({
        "title": "Paper Without Author",
        "year": "2024",
    })
    assert bad_meta.status == "invalid"
    assert any("Missing required field: 'authors'" in n for n in bad_meta.validation_notes)
