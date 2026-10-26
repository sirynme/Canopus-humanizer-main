"""Rules loader for canopus-humanizer legacy engine."""

import json
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PRIMARY_RULE_FILES = ("synonyms.json", "phrases.json")


def is_valid_rules_dir(candidate: Path) -> bool:
    """
    Verify that candidate path is a directory and contains intended rule JSON files.
    Does not assume directory name alone proves it is the correct rules source.
    """
    if not candidate.is_dir():
        return False
    return any((candidate / f).is_file() for f in PRIMARY_RULE_FILES)


def get_rules_dir() -> Path:
    """
    Resolve rules directory path containing intended JSON rule files.
    Does not assume the directory name alone proves it is the correct rules source.
    Searches explicit environment variables and standard directory hierarchy.
    """
    # 1. Environment variable override
    env_dir = os.getenv("CANOPUS_RULES_DIR") or os.getenv("RULES_DIR")
    if env_dir:
        candidate = Path(env_dir).resolve()
        if is_valid_rules_dir(candidate):
            return candidate
        warnings.warn(
            f"Configured rules directory '{env_dir}' does not contain expected rule files.",
            UserWarning,
            stacklevel=2,
        )

    # 2. Search hierarchy from current file upwards
    current = Path(__file__).resolve().parent
    search_roots = [
        current,                              # .../canopus_humanizer/core
        current.parent,                       # .../canopus_humanizer
        current.parent.parent,                # .../src
        current.parent.parent.parent,         # .../backend
        current.parent.parent.parent.parent,  # repository root
    ]

    for root in search_roots:
        for sub in ["rules", "backend/rules"]:
            candidate = (root / sub).resolve()
            if is_valid_rules_dir(candidate):
                return candidate

    # 3. Explicit warning if no directory containing intended rule files was found
    fallback = (Path(__file__).resolve().parent.parent.parent / "rules").resolve()
    warnings.warn(
        f"Failed to locate a valid rules directory containing JSON rule assets ({PRIMARY_RULE_FILES}). "
        f"Falling back to: '{fallback}'.",
        RuntimeWarning,
        stacklevel=2,
    )
    return fallback


def clean_rule_data(data: Any) -> Any:
    """Filter out metadata header blocks from JSON dictionaries or lists."""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k != "__prompt__"}
    elif isinstance(data, list):
        filtered = []
        for item in data:
            if isinstance(item, dict) and "__prompt__" in item and len(item) == 1:
                continue
            filtered.append(item)
        return filtered
    return data


def load_json_rule(filename: str, default: Any = None) -> Any:
    """Safely load and sanitize a JSON rule file with explicit warnings on failure."""
    rules_dir = get_rules_dir()
    path = rules_dir / filename
    if not path.is_file():
        warnings.warn(
            f"Rule file '{filename}' not found in rules directory '{rules_dir}'.",
            UserWarning,
            stacklevel=2,
        )
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return clean_rule_data(raw)
    except Exception as e:
        warnings.warn(
            f"Failed to load or parse rule file '{filename}' from '{path}': {e}",
            UserWarning,
            stacklevel=2,
        )
        return default if default is not None else {}


# Mutable rule asset containers
SYNONYMS: Dict[str, List[str]] = {}
PHRASES: List[Tuple[str, str]] = []
HEDGE_WORDS: List[str] = []
DETERMINERS: Dict[str, List[str]] = {}
CONJUNCTIONS: List[str] = []
PROTECTED_TERMS: Set[str] = set()
TRANSITIONS: Dict[str, List[str]] = {}
NOMINALIZATIONS: Dict[str, str] = {}
APPOSITIVES: Dict[str, str] = {}
DISCOURSE_MARKERS: Dict[str, List[str]] = {}


def reload_rules() -> None:
    """Reload all JSON rule assets into the in-place containers from the resolved rules directory."""
    global SYNONYMS, PHRASES, HEDGE_WORDS, DETERMINERS, CONJUNCTIONS
    global PROTECTED_TERMS, TRANSITIONS, NOMINALIZATIONS, APPOSITIVES, DISCOURSE_MARKERS

    SYNONYMS.clear()
    SYNONYMS.update(load_json_rule("synonyms.json", {}))

    PHRASES.clear()
    PHRASES.extend([tuple(pair) for pair in load_json_rule("phrases.json", [])])

    HEDGE_WORDS.clear()
    HEDGE_WORDS.extend(load_json_rule("hedge_words.json", []))

    DETERMINERS.clear()
    DETERMINERS.update(load_json_rule("determiners.json", {}))

    CONJUNCTIONS.clear()
    CONJUNCTIONS.extend(load_json_rule("conjunctions.json", []))

    PROTECTED_TERMS.clear()
    PROTECTED_TERMS.update(set(load_json_rule("protected_terms.json", [])))

    TRANSITIONS.clear()
    TRANSITIONS.update(load_json_rule("transitions.json", {}))

    NOMINALIZATIONS.clear()
    NOMINALIZATIONS.update(load_json_rule("nominalizations.json", {}))

    APPOSITIVES.clear()
    APPOSITIVES.update(load_json_rule("appositives.json", {}))

    DISCOURSE_MARKERS.clear()
    DISCOURSE_MARKERS.update(load_json_rule("discourse_markers.json", {}))

    if not SYNONYMS and not PHRASES:
        warnings.warn(
            "Legacy rules reload completed but essential rules (synonyms/phrases) are empty.",
            RuntimeWarning,
            stacklevel=2,
        )


def are_rules_loaded() -> bool:
    """Check if essential rule assets are populated."""
    return bool(SYNONYMS or PHRASES)


# Initial load at import time
reload_rules()
