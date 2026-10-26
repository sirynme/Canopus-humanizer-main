"""Deterministic transformation operations and case preservation logic."""

import re
from typing import List, Optional, Sequence, Tuple

from canopus_humanizer.engine.models import Change
from canopus_humanizer.rules.schema import RuleDefinition


def preserve_case_pattern(original: str, replacement: str) -> str:
    """Matches the capitalization pattern of the original string on the replacement."""
    if not original or not replacement:
        return replacement

    if original.isupper():
        return replacement.upper()

    if original[0].isupper():
        # Title/Capitalized case
        return replacement[0].upper() + replacement[1:]

    if original.islower():
        return replacement.lower()

    return replacement


def find_candidate_matches(text: str, rule: RuleDefinition) -> List[Change]:
    """
    Finds all valid non-overlapping matches for a rule within a given text string.
    Returns list of Change objects with exact character coordinates.
    """
    changes: List[Change] = []
    pattern = rule.pattern
    replacement = rule.replacement
    op = rule.operation

    if op == "terminology_lock":
        # Terminology lock is an immutable guard, not a mutation
        return []

    flags = 0 if rule.case_sensitive else re.IGNORECASE

    if op in ("replace_exact", "remove_redundancy"):
        # Match whole word boundaries if pattern consists of word characters
        is_word_seq = bool(re.match(r"^\w+(?:\s+\w+)*$", pattern))
        if is_word_seq:
            regex_str = rf"\b{re.escape(pattern)}\b"
        else:
            regex_str = re.escape(pattern)

        for m in re.finditer(regex_str, text, flags=flags):
            orig = m.group(0)
            rep = preserve_case_pattern(orig, replacement) if rule.preserve_case else replacement
            changes.append(
                Change(
                    rule_id=rule.id,
                    start=m.start(),
                    end=m.end(),
                    before=orig,
                    after=rep,
                    category=rule.category,
                    requires_review=rule.requires_review,
                )
            )

    elif op == "regex_replace":
        for m in re.finditer(pattern, text, flags=flags):
            orig = m.group(0)
            rep = preserve_case_pattern(orig, replacement) if rule.preserve_case else replacement
            changes.append(
                Change(
                    rule_id=rule.id,
                    start=m.start(),
                    end=m.end(),
                    before=orig,
                    after=rep,
                    category=rule.category,
                    requires_review=rule.requires_review,
                )
            )

    elif op == "manual_suggestion":
        # Mark as requiring human review
        for m in re.finditer(re.escape(pattern), text, flags=flags):
            orig = m.group(0)
            rep = preserve_case_pattern(orig, replacement) if rule.preserve_case else replacement
            changes.append(
                Change(
                    rule_id=rule.id,
                    start=m.start(),
                    end=m.end(),
                    before=orig,
                    after=rep,
                    category=rule.category,
                    requires_review=True,
                )
            )

    return changes


def apply_changes_to_text(text: str, changes: Sequence[Change]) -> str:
    """
    Applies approved changes to text in reverse offset order (from end to beginning).
    This strictly prevents offset drift without mutating the original buffer.
    """
    # Sort changes by start offset descending
    sorted_changes = sorted(changes, key=lambda c: c.start, reverse=True)
    result = text

    for c in sorted_changes:
        s, e = c.start, c.end
        # Verify text at slice matches before text
        if result[s:e] == c.before:
            result = result[:s] + c.after + result[e:]
        else:
            # Fallback if minor offset discrepancy
            pass

    return result
