"""Schema definition and validation for Canopus rule packs."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set

from canopus_humanizer.engine.errors import RulesetError, RULESET_INVALID


VALID_CATEGORIES = {
    "formatting",
    "grammar",
    "clarity",
    "redundancy",
    "terminology",
    "citation_format",
    "document_structure",
    "style",
}

VALID_RISKS = {"low", "medium", "high"}

VALID_OPERATIONS = {
    "replace_exact",
    "regex_replace",
    "remove_redundancy",
    "terminology_lock",
    "format_citation",
    "manual_suggestion",
}


@dataclass(frozen=True)
class RuleDefinition:
    """Strongly-typed rule contract."""
    id: str
    enabled: bool
    category: str
    risk: str
    operation: str
    pattern: str
    replacement: str = ""
    case_sensitive: bool = False
    priority: int = 100
    requires_review: bool = False
    preserve_case: bool = True
    source_note: str = ""


@dataclass(frozen=True)
class RulesetDefinition:
    """Strongly-typed ruleset container."""
    schema_version: str
    ruleset_id: str
    version: str
    language: str
    rules: List[RuleDefinition]
    content_hash: str = ""


def validate_ruleset_dict(data: Dict[str, Any]) -> RulesetDefinition:
    """Validates raw dictionary representation of a ruleset against schema."""
    if not isinstance(data, dict):
        raise RulesetError("Ruleset must be a JSON object", code=RULESET_INVALID)

    for req_field in ["schema_version", "ruleset_id", "version", "language", "rules"]:
        if req_field not in data:
            raise RulesetError(f"Missing required ruleset field '{req_field}'", code=RULESET_INVALID)

    schema_version = str(data["schema_version"]).strip()
    if schema_version != "1.0":
        raise RulesetError(f"Unsupported schema_version '{schema_version}', expected '1.0'", code=RULESET_INVALID)

    ruleset_id = str(data["ruleset_id"]).strip()
    if not ruleset_id:
        raise RulesetError("ruleset_id cannot be empty", code=RULESET_INVALID)

    version = str(data["version"]).strip()
    language = str(data["language"]).strip()

    raw_rules = data["rules"]
    if not isinstance(raw_rules, list):
        raise RulesetError("'rules' must be a list of rule definitions", code=RULESET_INVALID)

    parsed_rules: List[RuleDefinition] = []
    seen_ids: Set[str] = set()

    for idx, r in enumerate(raw_rules):
        if not isinstance(r, dict):
            raise RulesetError(f"Rule at index {idx} is not an object", code=RULESET_INVALID)

        # Check required rule fields
        for r_field in ["id", "enabled", "category", "risk", "operation", "pattern"]:
            if r_field not in r:
                raise RulesetError(f"Rule at index {idx} missing required field '{r_field}'", code=RULESET_INVALID)

        r_id = str(r["id"]).strip()
        if not r_id:
            raise RulesetError(f"Rule at index {idx} has empty ID", code=RULESET_INVALID)

        if r_id in seen_ids:
            raise RulesetError(f"Duplicate rule ID '{r_id}' detected", code=RULESET_INVALID)
        seen_ids.add(r_id)

        category = str(r["category"]).strip().lower()
        if category not in VALID_CATEGORIES:
            raise RulesetError(
                f"Rule '{r_id}' has invalid category '{category}'. Valid: {sorted(VALID_CATEGORIES)}",
                code=RULESET_INVALID,
            )

        risk = str(r["risk"]).strip().lower()
        if risk not in VALID_RISKS:
            raise RulesetError(
                f"Rule '{r_id}' has invalid risk '{risk}'. Valid: {sorted(VALID_RISKS)}",
                code=RULESET_INVALID,
            )

        operation = str(r["operation"]).strip().lower()
        if operation not in VALID_OPERATIONS:
            raise RulesetError(
                f"Rule '{r_id}' has invalid operation '{operation}'. Valid: {sorted(VALID_OPERATIONS)}",
                code=RULESET_INVALID,
            )

        pattern = str(r["pattern"])
        if not pattern:
            raise RulesetError(f"Rule '{r_id}' pattern cannot be empty", code=RULESET_INVALID)

        replacement = str(r.get("replacement", ""))
        enabled = bool(r["enabled"])
        case_sensitive = bool(r.get("case_sensitive", False))
        priority = int(r.get("priority", 100))
        requires_review = bool(r.get("requires_review", False))
        preserve_case = bool(r.get("preserve_case", True))
        source_note = str(r.get("source_note", ""))

        parsed_rules.append(
            RuleDefinition(
                id=r_id,
                enabled=enabled,
                category=category,
                risk=risk,
                operation=operation,
                pattern=pattern,
                replacement=replacement,
                case_sensitive=case_sensitive,
                priority=priority,
                requires_review=requires_review,
                preserve_case=preserve_case,
                source_note=source_note,
            )
        )

    return RulesetDefinition(
        schema_version=schema_version,
        ruleset_id=ruleset_id,
        version=version,
        language=language,
        rules=parsed_rules,
    )
