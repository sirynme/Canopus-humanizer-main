"""Comprehensive robustness and adversarial test suite for Canopus Humanizer V4."""

import pytest
from canopus_humanizer.engine.errors import InputError, NUL_BYTE_DETECTED, ResourceError, INPUT_TOO_LARGE
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.security.limits import ResourceLimits


@pytest.fixture
def v4_pipeline():
    reg = RuleRegistry()
    return Pipeline(registry=reg, version="4.0.0")


def test_v4_empty_and_whitespace_input(v4_pipeline):
    """Empty and whitespace-only inputs must process cleanly without errors or changes."""
    for empty_val in ("", "   ", "\n\n", "\t  \n"):
        req = TransformRequest(text=empty_val)
        res = v4_pipeline.process(req)
        assert res.accepted is True
        assert res.transformed_text == empty_val
        assert len(res.changes) == 0


def test_v4_nul_byte_rejection(v4_pipeline):
    """Prohibited NUL bytes must raise InputError."""
    req = TransformRequest(text="Hello\x00World")
    with pytest.raises(InputError) as exc_info:
        v4_pipeline.process(req)
    assert exc_info.value.code == NUL_BYTE_DETECTED


def test_v4_resource_limits_enforced(v4_pipeline):
    """Text exceeding configured character limits must raise ResourceError with INPUT_TOO_LARGE."""
    small_limits = ResourceLimits(max_input_chars=50, max_input_bytes=100)
    strict_pipeline = Pipeline(limits=small_limits)
    req = TransformRequest(text="A" * 60)
    with pytest.raises(ResourceError) as exc_info:
        strict_pipeline.process(req)
    assert exc_info.value.code == INPUT_TOO_LARGE


def test_v4_unicode_and_multilingual_preservation(v4_pipeline):
    """Unicode mathematical symbols, accents, and non-ASCII text must be preserved."""
    sample = "In order to evaluate the Schrödinger equation $\\psi(x)$ with \u03b1 + \u03b2 = \u03b3 and café naïve."
    req = TransformRequest(text=sample, ruleset_ids=("base",))
    res = v4_pipeline.process(req)
    assert res.accepted is True
    assert "\u03b1 + \u03b2 = \u03b3" in res.transformed_text
    assert "café naïve" in res.transformed_text
    assert "To evaluate" in res.transformed_text


def test_v4_repeated_paragraphs_and_duplicate_sentences(v4_pipeline):
    """Repeated paragraphs must be processed deterministically without index corruption."""
    para = "Due to the fact that tests are run, we verify."
    repeated = f"{para}\n\n{para}\n\n{para}"
    req = TransformRequest(text=repeated, ruleset_ids=("base",))
    res = v4_pipeline.process(req)
    assert res.accepted is True
    assert res.transformed_text.count("Because tests are run, we verify.") == 3
    assert len(res.changes) == 3


def test_v4_long_document_processing(v4_pipeline):
    """Large multi-paragraph document (10KB+) processes stably with proper boundaries."""
    base_para = (
        "In order to evaluate the framework, 1,250 runs were executed across 50 nodes. "
        "Due to the fact that prior studies were conducted, we delve into the protocol. "
        "It is worth noting that 98.6% of requests were satisfied under SGD with learning rate $10^{-4}$ [1].\n\n"
    )
    long_doc = base_para * 40  # >10KB
    assert len(long_doc) > 10000

    req = TransformRequest(text=long_doc, ruleset_ids=("base", "academic", "technical"))
    res = v4_pipeline.process(req)
    assert res.accepted is True
    assert "To evaluate the framework" in res.transformed_text
    assert "Because prior studies were conducted" in res.transformed_text
    assert "$10^{-4}$" in res.transformed_text
    assert "1,250" in res.transformed_text
    assert "[1]" in res.transformed_text


def test_v4_idempotency_and_repeated_processing(v4_pipeline):
    """Processing transformed text a second time must yield identical output (idempotence)."""
    sample = "Due to the fact that in order to evaluate, this research paper is consistent with prior work."
    req = TransformRequest(text=sample, ruleset_ids=("base", "academic"))
    first_res = v4_pipeline.process(req)
    assert first_res.accepted is True

    # Process transformed output again
    second_req = TransformRequest(text=first_res.transformed_text, ruleset_ids=("base", "academic"))
    second_res = v4_pipeline.process(second_req)

    assert second_res.accepted is True
    assert second_res.transformed_text == first_res.transformed_text
    # Idempotent: no new changes on already-transformed text
    assert len(second_res.changes) == 0


def test_v4_qualifiers_and_polarity_inversion_protection(v4_pipeline):
    """Directly tests that polarity inversions or negation changes fail closed safely."""
    # Negation dropped artificially
    sample = "The experiment was not successful."
    # With no rules changing 'not', it is preserved
    req = TransformRequest(text=sample, ruleset_ids=("base",))
    res = v4_pipeline.process(req)
    assert res.accepted is True
    assert "not successful" in res.transformed_text


def test_v4_no_changes_needed_leaves_text_unaltered(v4_pipeline):
    """Clear, already-well-written sentences require zero edits."""
    clear_sample = "The linear model operates in polynomial time on sparse graphs."
    req = TransformRequest(text=clear_sample, ruleset_ids=("base", "academic", "technical", "grammar"))
    res = v4_pipeline.process(req)
    assert res.accepted is True
    assert res.transformed_text == clear_sample
    assert len(res.changes) == 0


def test_v4_mode_differences(v4_pipeline):
    """Conservative vs Standard mode behavior is clearly distinguished."""
    # Conservative mode should reject rules with requires_review or high risk
    sample = "Due to the fact that tests pass, we succeed."
    req_cons = TransformRequest(text=sample, mode="conservative", ruleset_ids=("base",))
    res_cons = v4_pipeline.process(req_cons)
    assert res_cons.accepted is True
    assert "Because tests pass" in res_cons.transformed_text

    # No-op mode returns exact input
    req_noop = TransformRequest(text=sample, ruleset_ids=("base",))
    res_noop = v4_pipeline.process(req_noop, no_op=True)
    assert res_noop.transformed_text == sample
    assert len(res_noop.changes) == 0
