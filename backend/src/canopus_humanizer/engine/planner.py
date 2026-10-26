"""Deterministic change planning, conflict resolution, and change-budget enforcement."""

from typing import List, Sequence, Set, Tuple

from canopus_humanizer.engine.errors import RULE_CONFLICT
from canopus_humanizer.engine.models import Change, ProtectedSpan, ValidationIssue
from canopus_humanizer.engine.transforms import find_candidate_matches
from canopus_humanizer.rules.schema import RuleDefinition


class ChangePlanner:
    """Plans transformations deterministically, resolving overlapping rules and budget limits."""

    def __init__(self, max_changes: int = 500, mode: str = "conservative"):
        self.max_changes = max_changes
        self.mode = mode

    def plan(
        self,
        text: str,
        rules: Sequence[Tuple[str, RuleDefinition]],
        protected_spans: Sequence[ProtectedSpan] = (),
        placeholder_tokens: Sequence[str] = (),
    ) -> Tuple[Tuple[Change, ...], Tuple[ValidationIssue, ...]]:
        """
        Generates an approved list of non-conflicting transformations.
        Deterministic guarantees:
        1. All candidate matches generated across all enabled rules.
        2. Filter out matches that intersect protected spans or placeholders.
        3. Sort candidates by:
           - Priority (descending)
           - Start offset (ascending)
           - End offset (descending, longer match first)
           - Rule ID (alphabetical)
        4. Greedily select non-overlapping candidates up to max_changes budget.
        5. Record conflicting or dropped candidates in issues.
        """
        all_candidates: List[Change] = []
        rule_map = {}

        # 1. Collect candidate matches
        for ruleset_id, rule in rules:
            rule_map[rule.id] = rule
            matches = find_candidate_matches(text, rule)
            all_candidates.extend(matches)

        # 2. Identify forbidden ranges (placeholders and protected regions)
        forbidden_ranges: List[Tuple[int, int]] = []
        for token in placeholder_tokens:
            start = 0
            while True:
                idx = text.find(token, start)
                if idx == -1:
                    break
                forbidden_ranges.append((idx, idx + len(token)))
                start = idx + len(token)

        # 3. Filter out candidates intersecting forbidden ranges
        valid_candidates: List[Change] = []
        for cand in all_candidates:
            intersects_forbidden = False
            for f_start, f_end in forbidden_ranges:
                if not (cand.end <= f_start or cand.start >= f_end):
                    intersects_forbidden = True
                    break
            if not intersects_forbidden:
                valid_candidates.append(cand)

        # 4. Deterministic sorting
        # Priority DESC, Start ASC, Length DESC, Rule ID ASC
        valid_candidates.sort(
            key=lambda c: (
                -rule_map[c.rule_id].priority,
                c.start,
                -(c.end - c.start),
                c.rule_id,
            )
        )

        # 5. Greedy non-overlapping selection
        approved: List[Change] = []
        issues: List[ValidationIssue] = []
        occupied_ranges: List[Tuple[int, int, str]] = []

        for cand in valid_candidates:
            # Check for conflict with already approved changes
            overlapping_rule_id = None
            for occ_s, occ_e, occ_rule_id in occupied_ranges:
                if not (cand.end <= occ_s or cand.start >= occ_e):
                    overlapping_rule_id = occ_rule_id
                    break

            if overlapping_rule_id:
                issues.append(
                    ValidationIssue(
                        code=RULE_CONFLICT,
                        severity="info",
                        message=(
                            f"Rule '{cand.rule_id}' at [{cand.start}:{cand.end}] was skipped due to conflict "
                            f"with higher-priority rule '{overlapping_rule_id}'"
                        ),
                        start=cand.start,
                        end=cand.end,
                    )
                )
                continue

            # Respect mode requirements
            if self.mode == "conservative" and cand.requires_review:
                issues.append(
                    ValidationIssue(
                        code="MANUAL_REVIEW_REQUIRED",
                        severity="info",
                        message=f"Rule '{cand.rule_id}' requires manual review and was skipped in conservative mode.",
                        start=cand.start,
                        end=cand.end,
                    )
                )
                continue

            # Enforce max_changes budget
            if len(approved) >= self.max_changes:
                issues.append(
                    ValidationIssue(
                        code="MAX_CHANGES_EXCEEDED",
                        severity="warning",
                        message=f"Change limit of {self.max_changes} reached; skipping rule '{cand.rule_id}'",
                        start=cand.start,
                        end=cand.end,
                    )
                )
                continue

            approved.append(cand)
            occupied_ranges.append((cand.start, cand.end, cand.rule_id))

        return tuple(approved), tuple(issues)
