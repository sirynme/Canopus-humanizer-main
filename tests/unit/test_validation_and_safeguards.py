"""Unit tests for semantic and factual preservation safeguards."""

import pytest
from canopus_humanizer.engine.models import ProtectedSpan
from canopus_humanizer.engine.validation import OutputValidator


def test_validator_protected_span_mismatch():
    validator = OutputValidator()
    spans = [
        ProtectedSpan(
            span_id="s1",
            start=0,
            end=5,
            kind="formula",
            original="E=mc^2",
            detector="math",
        )
    ]
    # Transformed missing "E=mc^2"
    issues = validator.validate("Original has E=mc^2", "Transformed has dropped formula", spans)
    assert any(i.code == "PROTECTED_SPAN_MISMATCH" and i.severity == "error" for i in issues)


def test_validator_numeric_preservation():
    validator = OutputValidator()
    orig = "The benchmark achieved 98.6% with 1,250 samples."
    # Transformed altered 98.6% to 95.0%
    trans = "The benchmark achieved 95.0% with 1,250 samples."
    issues = validator.validate(orig, trans, [])
    assert any(i.code == "NUMERIC_VALUE_ALTERED" and i.severity == "error" for i in issues)


def test_validator_negation_preservation():
    validator = OutputValidator()
    orig = "The method is not suitable for realtime streams."
    # Transformed dropped "not", altering proposition
    trans = "The method is suitable for realtime streams."
    issues = validator.validate(orig, trans, [])
    assert any(i.code == "NEGATION_ALTERED" and i.severity == "error" for i in issues)


def test_validator_modal_qualification_drift():
    validator = OutputValidator()
    orig = "This approach may possibly yield improvements."
    # Transformed escalated to absolute certainty
    trans = "This approach must definitely yield improvements."
    issues = validator.validate(orig, trans, [])
    assert any(i.code == "SEMANTIC_DRIFT_DETECTED" and i.severity == "warning" for i in issues)
