"""Rule registry managing active rulesets and priority ordering."""

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from canopus_humanizer.engine.errors import RulesetError, RULE_NOT_FOUND
from canopus_humanizer.rules.loader import RulesetLoader
from canopus_humanizer.rules.schema import RuleDefinition, RulesetDefinition


def find_default_rulesets_dir() -> Path:
    """Finds the default rulesets directory across workspace locations."""
    current = Path(__file__).resolve().parent
    for p in [current, current.parent, current.parent.parent, current.parent.parent.parent, current.parent.parent.parent.parent]:
        candidate = p / "rulesets"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "rulesets"


class RuleRegistry:
    """Registry maintaining loaded rulesets with deterministic ordering and lookup."""

    def __init__(self, rulesets_dir: Optional[Union[str, Path]] = None):
        self._rulesets: Dict[str, RulesetDefinition] = {}
        self.rulesets_dir = Path(rulesets_dir) if rulesets_dir else find_default_rulesets_dir()
        if self.rulesets_dir.is_dir():
            self.load_directory(self.rulesets_dir)

    def register_ruleset(self, ruleset: RulesetDefinition) -> None:
        """Registers a parsed RulesetDefinition in the registry."""
        self._rulesets[ruleset.ruleset_id] = ruleset

    def load_directory(self, directory: Union[str, Path]) -> int:
        """Loads all .json rule pack files found directly inside a directory."""
        dir_path = Path(directory).resolve()
        if not dir_path.is_dir():
            return 0

        count = 0
        for json_file in sorted(dir_path.glob("*.json")):
            try:
                rs = RulesetLoader.load_from_file(json_file)
                self.register_ruleset(rs)
                count += 1
            except Exception:
                # Skip files not adhering to ruleset schema
                pass
        return count

    def get_ruleset(self, ruleset_id: str) -> RulesetDefinition:
        """Retrieves a registered ruleset by ID, or raises RulesetError."""
        if ruleset_id not in self._rulesets:
            raise RulesetError(f"Ruleset '{ruleset_id}' not found in registry", code=RULE_NOT_FOUND)
        return self._rulesets[ruleset_id]

    def has_ruleset(self, ruleset_id: str) -> bool:
        return ruleset_id in self._rulesets

    def get_enabled_rules(self, ruleset_ids: Sequence[str]) -> List[Tuple[str, RuleDefinition]]:
        """
        Retrieves all enabled rules from the specified ruleset IDs.
        Guarantees deterministic ordering:
        Sorts primarily by priority descending, then by rule ID ascending.
        Returns list of (ruleset_id, RuleDefinition).
        """
        rules_with_source: List[Tuple[str, RuleDefinition]] = []
        for r_id in ruleset_ids:
            rs = self.get_ruleset(r_id)
            for rule in rs.rules:
                if rule.enabled:
                    rules_with_source.append((r_id, rule))

        # Deterministic sorting: priority DESC, then rule ID ASC
        rules_with_source.sort(key=lambda item: (-item[1].priority, item[1].id))
        return rules_with_source

    def get_version_info(self, ruleset_ids: Sequence[str]) -> Tuple[str, ...]:
        """Returns version and hash tuple for the requested ruleset IDs."""
        versions = []
        for r_id in ruleset_ids:
            if r_id in self._rulesets:
                rs = self._rulesets[r_id]
                versions.append(f"{rs.ruleset_id}@{rs.version}:{rs.content_hash[:8]}")
        return tuple(versions)
