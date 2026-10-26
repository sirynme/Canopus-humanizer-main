"""Unit tests for unified diff and audit logging."""

import json
import pytest
from canopus_humanizer.engine.diff import generate_unified_diff, format_change_log
from canopus_humanizer.engine.models import Change
from canopus_humanizer.observability.audit import AuditEvent, AuditLogger


def test_unified_diff_generation():
    orig = "Line 1\nDue to the fact that we test\nLine 3"
    trans = "Line 1\nBecause we test\nLine 3"

    diff = generate_unified_diff(orig, trans)
    assert "-Due to the fact that we test" in diff
    assert "+Because we test" in diff


def test_format_change_log():
    c = Change(
        rule_id="r1",
        start=0,
        end=5,
        before="Hello",
        after="Hi",
        category="style",
        requires_review=True,
    )
    log_str = format_change_log([c])
    assert "[STYLE]" in log_str
    assert "[NEEDS REVIEW]" in log_str
    assert "Rule: r1" in log_str


def test_audit_event_does_not_contain_raw_text():
    event = AuditEvent(
        timestamp=1000.0,
        request_id="req123",
        engine_version="1.0.0",
        ruleset_versions=("base@1.0.0:hash",),
        duration_ms=12.5,
        status="success",
        input_char_count=50,
        output_char_count=45,
        modifications_count=2,
        rules_applied=("r1", "r2"),
        issues_count=0,
    )
    json_str = event.to_json()
    data = json.loads(json_str)

    # Assure no raw document text field exists in audit schema
    assert "text" not in data
    assert "document" not in data
    assert data["request_id"] == "req123"
    assert data["rules_applied"] == ["r1", "r2"]
