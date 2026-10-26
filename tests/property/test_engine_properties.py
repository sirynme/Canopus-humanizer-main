"""Property-based tests for deterministic invariants, no-op exactness, and protection."""

import pytest
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.rules.schema import RuleDefinition, RulesetDefinition


@pytest.fixture
def pipeline():
    reg = RuleRegistry()
    return Pipeline(registry=reg)


def test_property_noop_returns_exact_original(pipeline):
    """Property: No-op mode always returns the original string byte-for-byte identical."""
    samples = [
        "",
        "   ",
        "Simple plain text.",
        "Equations $E=mc^2$ and [1] citations with 98.6% numbers.",
        "Multi-line\n\nParagraph with complex Unicode: \u03b1 + \u03b2 = \u03b3.",
    ]
    for sample in samples:
        req = TransformRequest(text=sample)
        res = pipeline.process(req, no_op=True)
        assert res.transformed_text == sample
        assert len(res.changes) == 0
        assert res.accepted is True


def test_property_zero_enabled_rules_yields_identical_text(pipeline):
    """Property: Applying no rules or empty ruleset yields unchanged text."""
    sample = "Due to the fact that we have no rules enabled, nothing changes."
    req = TransformRequest(text=sample, ruleset_ids=())
    res = pipeline.process(req)
    assert res.transformed_text == sample
    assert len(res.changes) == 0


def test_property_determinism_across_multiple_runs(pipeline):
    """Property: Exactly identical input, configuration, and rulesets produce identical output across repeated runs."""
    sample = (
        "Due to the fact that previous studies have shown 98.6% accuracy [1], "
        "we delve into this research paper in order to evaluate."
    )
    req = TransformRequest(text=sample, ruleset_ids=("base", "academic"))

    baseline_res = pipeline.process(req)
    for _ in range(10):
        run_res = pipeline.process(req)
        assert run_res.transformed_text == baseline_res.transformed_text
        assert run_res.changes == baseline_res.changes
        assert run_res.accepted == baseline_res.accepted


def test_property_protected_spans_byte_for_byte_preserved(pipeline):
    """Property: All protected tokens (math, citations, numbers, units) remain byte-for-byte identical."""
    protected_tokens = [
        "$f(x) = \\frac{1}{1 + e^{-x}}$",
        "[1, 2]",
        "(Smith & Taylor, 2024)",
        "98.6%",
        "$4.5 million",
        "100 queries per second",
        "https://example.com/api",
    ]
    sample = f"Evaluating due to the fact that {', '.join(protected_tokens)} are tested."
    req = TransformRequest(text=sample, ruleset_ids=("base",))

    res = pipeline.process(req)
    assert res.accepted is True
    for token in protected_tokens:
        assert token in res.transformed_text


def test_property_rule_precedence_determinism():
    """Property: Rule execution precedence is determined strictly by priority, not declaration order."""
    rule_low = RuleDefinition(
        id="r_low",
        enabled=True,
        category="style",
        risk="low",
        operation="replace_exact",
        pattern="test case",
        replacement="low priority replacement",
        priority=10,
    )
    rule_high = RuleDefinition(
        id="r_high",
        enabled=True,
        category="style",
        risk="low",
        operation="replace_exact",
        pattern="test case",
        replacement="high priority replacement",
        priority=100,
    )

    # Order 1: low declared before high
    rs1 = RulesetDefinition("1.0", "rs1", "1.0.0", "en", [rule_low, rule_high], "h1")
    reg1 = RuleRegistry(rulesets_dir=None)
    reg1.register_ruleset(rs1)
    pipe1 = Pipeline(registry=reg1)
    res1 = pipe1.process(TransformRequest(text="This is a test case.", ruleset_ids=("rs1",)))

    # Order 2: high declared before low
    rs2 = RulesetDefinition("1.0", "rs2", "1.0.0", "en", [rule_high, rule_low], "h2")
    reg2 = RuleRegistry(rulesets_dir=None)
    reg2.register_ruleset(rs2)
    pipe2 = Pipeline(registry=reg2)
    res2 = pipe2.process(TransformRequest(text="This is a test case.", ruleset_ids=("rs2",)))

    assert res1.transformed_text == "This is a high priority replacement."
    assert res2.transformed_text == "This is a high priority replacement."
    assert res1.transformed_text == res2.transformed_text
