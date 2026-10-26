"""Stage 4: Identification of specific editing opportunities based on document needs."""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

from canopus_humanizer.engine.classifier import DocumentClassification
from canopus_humanizer.engine.models import Change
from canopus_humanizer.engine.transforms import find_candidate_matches
from canopus_humanizer.rules.schema import RuleDefinition


@dataclass(frozen=True)
class EditingOpportunity:
    """A verified editing opportunity mapped to a rule and exact offsets."""
    change: Change
    rule: RuleDefinition
    ruleset_id: str
    need_category: str  # "grammar", "redundancy", "clarity", "style", "terminology"


class OpportunityDetector:
    """Identifies concrete editing opportunities without forcing every rule on every input."""

    def detect_opportunities(
        self,
        text: str,
        rules: Sequence[Tuple[str, RuleDefinition]],
        classification: DocumentClassification,
        mode: str = "conservative",
    ) -> List[EditingOpportunity]:
        """
        Scans text for concrete editing opportunities matching document needs.
        
        Rules:
        1. If document is classified as 'is_already_clear' and mode is 'conservative',
           stylistic/optional rewrites are suppressed to avoid unnecessary edits.
        2. High-value grammar, redundancy pruning, and terminology locks are always evaluated.
        3. Filters rules by category according to identified document needs.
        """
        opportunities: List[EditingOpportunity] = []

        for ruleset_id, rule in rules:
            if not rule.enabled:
                continue

            # In conservative mode on already-clear text:
            # Skip pure stylistic transformations if document is already well-written
            if classification.is_already_clear and mode == "conservative":
                if rule.category in ("style", "formatting") and rule.risk != "low":
                    continue
                # Also skip transition churn if text is already clear
                if "furthermore" in rule.id.lower() or "transition" in rule.id.lower():
                    continue

            # In conservative mode, skip rules requiring manual review or high risk
            if mode == "conservative" and (rule.requires_review or rule.risk in ("medium", "high")):
                continue

            matches = find_candidate_matches(text, rule)
            for m in matches:
                need_cat = rule.category
                opportunities.append(
                    EditingOpportunity(
                        change=m,
                        rule=rule,
                        ruleset_id=ruleset_id,
                        need_category=need_cat,
                    )
                )

        return opportunities
