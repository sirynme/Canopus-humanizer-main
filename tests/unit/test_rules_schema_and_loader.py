"""Unit tests for ruleset schema validation, loading, and registry."""

import json
import pytest

from canopus_humanizer.engine.errors import RulesetError
from canopus_humanizer.rules.loader import RulesetLoader
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.rules.schema import RuleDefinition, RulesetDefinition, validate_ruleset_dict


def test_valid_ruleset_validation():
    valid_dict = {
        "schema_version": "1.0",
        "ruleset_id": "test_rules",
        "version": "1.0.0",
        "language": "en",
        "rules": [
            {
                "id": "style.test_001",
                "enabled": True,
                "category": "style",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "foo",
                "replacement": "bar",
                "priority": 100,
            }
        ],
    }
    rs = validate_ruleset_dict(valid_dict)
    assert rs.ruleset_id == "test_rules"
    assert len(rs.rules) == 1
    assert rs.rules[0].replacement == "bar"


def test_missing_required_ruleset_field():
    invalid_dict = {
        "schema_version": "1.0",
        "version": "1.0.0",
        # missing ruleset_id, language, rules
    }
    with pytest.raises(RulesetError):
        validate_ruleset_dict(invalid_dict)


def test_invalid_category_rejection():
    bad_cat_dict = {
        "schema_version": "1.0",
        "ruleset_id": "test_cat",
        "version": "1.0.0",
        "language": "en",
        "rules": [
            {
                "id": "test_001",
                "enabled": True,
                "category": "illegal_category",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "foo",
            }
        ],
    }
    with pytest.raises(RulesetError) as exc_info:
        validate_ruleset_dict(bad_cat_dict)
    assert "invalid category" in str(exc_info.value)


def test_duplicate_rule_id_rejection():
    duplicate_dict = {
        "schema_version": "1.0",
        "ruleset_id": "test_dup",
        "version": "1.0.0",
        "language": "en",
        "rules": [
            {
                "id": "duplicate_id",
                "enabled": True,
                "category": "clarity",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "foo",
            },
            {
                "id": "duplicate_id",
                "enabled": True,
                "category": "clarity",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "bar",
            },
        ],
    }
    with pytest.raises(RulesetError) as exc_info:
        validate_ruleset_dict(duplicate_dict)
    assert "Duplicate rule ID" in str(exc_info.value)


def test_loader_content_hash():
    content = json.dumps({
        "schema_version": "1.0",
        "ruleset_id": "hash_test",
        "version": "1.0.0",
        "language": "en",
        "rules": [
            {
                "id": "r1",
                "enabled": True,
                "category": "clarity",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "abc",
                "replacement": "def",
            }
        ]
    })
    rs = RulesetLoader.load_from_string(content)
    assert len(rs.content_hash) == 64  # SHA-256


def test_registry_priority_sorting():
    rs = RulesetDefinition(
        schema_version="1.0",
        ruleset_id="priority_test",
        version="1.0.0",
        language="en",
        rules=[
            RuleDefinition(
                id="rule_low",
                enabled=True,
                category="clarity",
                risk="low",
                operation="replace_exact",
                pattern="a",
                priority=10,
            ),
            RuleDefinition(
                id="rule_high",
                enabled=True,
                category="clarity",
                risk="low",
                operation="replace_exact",
                pattern="b",
                priority=200,
            ),
            RuleDefinition(
                id="rule_mid",
                enabled=True,
                category="clarity",
                risk="low",
                operation="replace_exact",
                pattern="c",
                priority=100,
            ),
        ],
        content_hash="mock",
    )
    reg = RuleRegistry(rulesets_dir=None)
    reg.register_ruleset(rs)

    sorted_rules = reg.get_enabled_rules(["priority_test"])
    ids = [r[1].id for r in sorted_rules]
    assert ids == ["rule_high", "rule_mid", "rule_low"]
