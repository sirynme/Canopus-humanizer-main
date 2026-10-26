"""Unit tests for edge cases, Unicode, multilingual text, and adversarial inputs."""

import pytest
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry


@pytest.fixture
def pipeline():
    return Pipeline(registry=RuleRegistry())


def test_empty_and_whitespace_input(pipeline):
    # Empty input
    req_empty = TransformRequest(text="", ruleset_ids=("base",))
    res_empty = pipeline.process(req_empty)
    assert res_empty.transformed_text == ""
    assert res_empty.accepted is True
    assert len(res_empty.changes) == 0

    # Whitespace only input
    req_ws = TransformRequest(text="   \n\t  \n  ", ruleset_ids=("base",))
    res_ws = pipeline.process(req_ws)
    assert res_ws.transformed_text == "   \n\t  \n  "
    assert res_ws.accepted is True


def test_unicode_and_multilingual_text(pipeline):
    text = (
        "Due to the fact that \u00e4pfel und \u00f6l are tested with "
        "\u03b1-\u03b2 decay at 98.6% in M\u00fcnchen, we proceed."
    )
    req = TransformRequest(text=text, ruleset_ids=("base",))
    res = pipeline.process(req)

    assert res.accepted is True
    # Verify non-ASCII characters preserved intact
    assert "\u00e4pfel" in res.transformed_text
    assert "\u00f6l" in res.transformed_text
    assert "\u03b1-\u03b2" in res.transformed_text
    assert "M\u00fcnchen" in res.transformed_text
    assert "Because" in res.transformed_text


def test_adversarial_fake_placeholder_injection(pipeline):
    """
    Adversarial test: An input text deliberately containing an artificial placeholder string
    such as '<<CANOPUS_PROT_fake_123>>' must not confuse the internal nonce-based placeholder registry.
    """
    text = (
        "Due to the fact that input contains <<CANOPUS_PROT_fake_123>> and 98.6%, "
        "we verify restoration integrity."
    )
    req = TransformRequest(text=text, ruleset_ids=("base",))
    res = pipeline.process(req)

    assert res.accepted is True
    assert "<<CANOPUS_PROT_fake_123>>" in res.transformed_text
    assert "98.6%" in res.transformed_text
    assert "Because" in res.transformed_text


def test_repeated_processing_idempotence(pipeline):
    """Verifies that processing an already transformed text produces a stable result without infinite drift."""
    text = "Due to the fact that prior studies were conducted, we delve into this research paper."
    req = TransformRequest(text=text, ruleset_ids=("base", "academic"))

    res1 = pipeline.process(req)
    assert res1.accepted is True

    # Re-process the output
    req2 = TransformRequest(text=res1.transformed_text, ruleset_ids=("base", "academic"))
    res2 = pipeline.process(req2)
    assert res2.accepted is True
    # Stable idempotent output: no further changes on the already transformed text
    assert res2.transformed_text == res1.transformed_text
    assert len(res2.changes) == 0
