"""Unified diff and change inspection reporting."""

import difflib
from typing import Sequence

from canopus_humanizer.engine.models import Change


def generate_unified_diff(
    original_text: str,
    transformed_text: str,
    from_file: str = "original.txt",
    to_file: str = "transformed.txt",
) -> str:
    """Generates standard unified diff lines between original and transformed text."""
    orig_lines = original_text.splitlines(keepends=True)
    trans_lines = transformed_text.splitlines(keepends=True)

    diff_iter = difflib.unified_diff(
        orig_lines,
        trans_lines,
        fromfile=from_file,
        tofile=to_file,
        lineterm="",
    )
    return "\n".join(diff_iter)


def format_change_log(changes: Sequence[Change]) -> str:
    """Formats list of applied changes for reviewable console or audit output."""
    if not changes:
        return "No transformations applied."

    lines = [f"Total Transformations: {len(changes)}", "----------------------------------------"]
    for idx, c in enumerate(changes, 1):
        review_flag = " [NEEDS REVIEW]" if c.requires_review else ""
        lines.append(
            f"{idx:03d}. [{c.category.upper()}] Rule: {c.rule_id}{review_flag}\n"
            f"     Offsets: [{c.start}:{c.end}]\n"
            f"     Before:  '{c.before}'\n"
            f"     After:   '{c.after}'"
        )
    return "\n".join(lines)
