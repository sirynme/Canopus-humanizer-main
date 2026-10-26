"""Unit tests for change planning, transforms, case preservation, and conflict resolution."""

import pytest
from canopus_humanizer.engine.models import Change
from canopus_humanizer.engine.planner import ChangePlanner
from canopus_humanizer.engine.transforms import apply_changes_to_text, preserve_case_pattern
from canopus_humanizer.rules.schema import RuleDefinition


def test_preserve_case_pattern():
    assert preserve_case_pattern("DUE TO THE FACT THAT", "because") == "BECAUSE"
    assert preserve_case_pattern("Due to the fact that", "because") == "Because"
    assert preserve_case_pattern("due to the fact that", "because") == "because"


def test_apply_changes_reverse_offset_prevents_drift():
    text = "The alpha parameter and beta parameter are tested."
    # Change 1: "alpha" (offset 4:9) -> "primary" (length 7)
    # Change 2: "beta" (offset 24:28) -> "secondary" (length 9)
    changes = [
        Change(
            rule_id="r1",
            start=4,
            end=9,
            before="alpha",
            after="primary",
            category="style",
            requires_review=False,
        ),
        Change(
            rule_id="r2",
            start=24,
            end=28,
            before="beta",
            after="secondary",
            category="style",
            requires_review=False,
        ),
    ]

    result = apply_changes_to_text(text, changes)
    assert result == "The primary parameter and secondary parameter are tested."


def test_planner_conflict_resolution_higher_priority_wins():
    text = "We should examine the entire system."
    # Rule 1: "examine the entire" -> "review the whole" (priority 100)
    # Rule 2: "the entire system" -> "all components" (priority 50)
    rule_high = RuleDefinition(
        id="rule_high",
        enabled=True,
        category="clarity",
        risk="low",
        operation="replace_exact",
        pattern="examine the entire",
        replacement="review the whole",
        priority=100,
    )
    rule_low = RuleDefinition(
        id="rule_low",
        enabled=True,
        category="clarity",
        risk="low",
        operation="replace_exact",
        pattern="the entire system",
        replacement="all components",
        priority=50,
    )

    planner = ChangePlanner()
    approved, issues = planner.plan(
        text=text,
        rules=[("rs", rule_high), ("rs", rule_low)],
    )

    assert len(approved) == 1
    assert approved[0].rule_id == "rule_high"
    assert len(issues) == 1
    assert issues[0].code == "RULE_CONFLICT"


def test_planner_budget_enforcement():
    text = "foo bar foo bar foo bar"
    rule = RuleDefinition(
        id="r_foo",
        enabled=True,
        category="style",
        risk="low",
        operation="replace_exact",
        pattern="foo",
        replacement="baz",
        priority=100,
    )

    planner = ChangePlanner(max_changes=2)
    approved, issues = planner.plan(
        text=text,
        rules=[("rs", rule)],
    )

    assert len(approved) == 2
    assert any(i.code == "MAX_CHANGES_EXCEEDED" for i in issues)
