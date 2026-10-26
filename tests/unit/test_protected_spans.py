"""Unit tests for protected span detection, overlapping resolution, and fail-closed restoration."""

import pytest
from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector, ProtectedSpanRegistry


def test_detect_math_and_currency_distinction():
    detector = ProtectedSpanDetector()
    text = "The formula is $f(x) = x^2$, while the cost was $25.00 or $4.5 million."
    spans = detector.detect(text)

    originals = [s.original for s in spans]
    kinds = {s.original: s.kind for s in spans}

    assert "$f(x) = x^2$" in originals
    assert kinds["$f(x) = x^2$"] == "math_inline"

    assert "$25.00" in originals
    assert kinds["$25.00"] == "currency"

    assert "$4.5 million" in originals
    assert kinds["$4.5 million"] == "currency"


def test_detect_latex_macros_and_citations():
    detector = ProtectedSpanDetector()
    text = r"Using \frac{a}{b} and citations [1, 2] and (Smith et al., 2024), we find results."
    spans = detector.detect(text)

    originals = [s.original for s in spans]
    assert r"\frac{a}{b}" in originals
    assert "[1, 2]" in originals
    assert "(Smith et al., 2024)" in originals


def test_detect_units_and_percentages():
    detector = ProtectedSpanDetector()
    text = "At 35 °C, the reaction yielded 98.6% with 100 queries per second."
    spans = detector.detect(text)

    originals = [s.original for s in spans]
    assert "35 °C" in originals
    assert "98.6%" in originals
    assert "100 queries per second" in originals


def test_overlap_resolution_code_block_priority():
    detector = ProtectedSpanDetector()
    text = "Here is code: ```python\nx = 100\n``` and inline `val = 42`."
    spans = detector.detect(text)

    originals = [s.original for s in spans]
    # Code block must be captured as single entity rather than nested numbers
    assert "```python\nx = 100\n```" in originals
    assert "`val = 42`" in originals
    assert "100" not in originals  # nested number was covered


def test_mask_and_restore_success():
    text = "Evaluating model at 98.6% accuracy in 2024 with citation [1]."
    detector = ProtectedSpanDetector()
    spans = detector.detect(text)
    registry = ProtectedSpanRegistry(spans)

    masked = registry.mask(text)
    assert "98.6%" not in masked
    assert "[1]" not in masked
    assert "2024" not in masked
    assert "<<CANOPUS_PROT_" in masked

    restored, ok, errors = registry.restore(masked, original_raw_text=text)
    assert ok is True
    assert errors == []
    assert restored == text


def test_mask_and_restore_fail_closed_on_dropped_placeholder():
    text = "Evaluating 98.6% accuracy."
    detector = ProtectedSpanDetector()
    spans = detector.detect(text)
    registry = ProtectedSpanRegistry(spans)

    masked = registry.mask(text)
    # Simulate an external corruption dropping the placeholder
    corrupted = "Evaluating nothing."

    restored, ok, errors = registry.restore(corrupted, original_raw_text=text)
    assert ok is False
    assert len(errors) > 0
    # Must fail closed and return original raw text
    assert restored == text
