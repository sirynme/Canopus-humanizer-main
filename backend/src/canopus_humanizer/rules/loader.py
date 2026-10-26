"""Safe ruleset loading from disk or string with hash tracking."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Union

from canopus_humanizer.engine.errors import RulesetError, RULESET_INVALID
from canopus_humanizer.rules.schema import RulesetDefinition, validate_ruleset_dict
from canopus_humanizer.security.limits import validate_regex_pattern


class RulesetLoader:
    """Loads and cryptographically fingerprints versioned rule packs."""

    @staticmethod
    def load_from_string(content: str) -> RulesetDefinition:
        """Parses ruleset JSON string, validates schema, and computes content hash."""
        if not content or not content.strip():
            raise RulesetError("Ruleset content cannot be empty", code=RULESET_INVALID)

        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise RulesetError(f"Malformed ruleset JSON: {e}", code=RULESET_INVALID)

        ruleset = validate_ruleset_dict(raw_data)

        # Validate regex patterns
        for rule in ruleset.rules:
            if rule.operation == "regex_replace":
                validate_regex_pattern(rule.pattern)

        # Compute SHA-256
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return RulesetDefinition(
            schema_version=ruleset.schema_version,
            ruleset_id=ruleset.ruleset_id,
            version=ruleset.version,
            language=ruleset.language,
            rules=ruleset.rules,
            content_hash=content_hash,
        )

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> RulesetDefinition:
        """Loads and validates a rule pack from a file on disk."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise RulesetError(f"Rule file does not exist: {path}", code="RULE_FILE_NOT_FOUND")
        if not path.is_file():
            raise RulesetError(f"Rule path is not a regular file: {path}", code=RULESET_INVALID)

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise RulesetError(f"Failed to read rule file {path}: {e}", code=RULESET_INVALID)

        return cls.load_from_string(content)
