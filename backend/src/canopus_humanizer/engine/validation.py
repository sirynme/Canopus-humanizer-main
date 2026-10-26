"""Semantic, factual, and structural output validation."""

import re
from typing import Dict, List, Sequence, Set, Tuple

from canopus_humanizer.engine.errors import (
    NEGATION_ALTERED,
    OUTPUT_VALIDATION_FAILED,
    PROTECTED_SPAN_MISMATCH,
    SEMANTIC_DRIFT_DETECTED,
)
from canopus_humanizer.engine.models import ProtectedSpan, ValidationIssue


NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "neither",
    "nor",
    "none",
    "cannot",
    "hardly",
    "scarcely",
    "barely",
    "without",
    "isnt",
    "isn't",
    "arent",
    "aren't",
    "wasnt",
    "wasn't",
    "werent",
    "weren't",
    "havent",
    "haven't",
    "hasnt",
    "hasn't",
    "hadnt",
    "hadn't",
    "wont",
    "won't",
    "wouldnt",
    "wouldn't",
    "cant",
    "can't",
    "couldnt",
    "couldn't",
    "shouldnt",
    "shouldn't",
    "doesnt",
    "doesn't",
    "dont",
    "don't",
    "didnt",
    "didn't",
}

CERTAINTY_MODALS = {
    "must",
    "shall",
    "always",
    "proven",
    "certain",
    "definitely",
    "strictly",
    "necessarily",
}

UNCERTAINTY_MODALS = {
    "may",
    "might",
    "could",
    "possibly",
    "plausible",
    "approximately",
    "roughly",
}

POSITIVE_DIRECTION_WORDS = {
    "increase",
    "increases",
    "increased",
    "increasing",
    "higher",
    "highest",
    "greater",
    "outperform",
    "outperforms",
    "outperformed",
    "superior",
    "enhance",
    "enhances",
    "enhanced",
    "positive",
    "gain",
    "growth",
}

NEGATIVE_DIRECTION_WORDS = {
    "decrease",
    "decreases",
    "decreased",
    "decreasing",
    "lower",
    "lowest",
    "less",
    "underperform",
    "inferior",
    "degrade",
    "degrades",
    "degraded",
    "negative",
    "loss",
    "reduction",
}


class OutputValidator:
    """Validates transformed output against original to guarantee semantic and factual integrity."""

    def __init__(
        self,
        strict_numbers: bool = True,
        strict_negation: bool = True,
        strict_citations: bool = True,
    ):
        self.strict_numbers = strict_numbers
        self.strict_negation = strict_negation
        self.strict_citations = strict_citations

    def extract_numbers(self, text: str) -> List[str]:
        """Extracts all numeric, percentage, and currency tokens."""
        pattern = r"\b\d+(?:,\d{3})*(?:\.\d+)?%?|\$\d+(?:,\d{3})*(?:\.\d+)?"
        return re.findall(pattern, text)

    def extract_negation_tokens(self, text: str) -> List[str]:
        """Finds all explicit negation tokens in text."""
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        return [w for w in words if w in NEGATION_WORDS]

    def extract_modals(self, text: str) -> Tuple[List[str], List[str]]:
        """Extracts certainty and uncertainty modal words."""
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        certain = [w for w in words if w in CERTAINTY_MODALS]
        uncertain = [w for w in words if w in UNCERTAINTY_MODALS]
        return certain, uncertain

    def validate(
        self,
        original_text: str,
        transformed_text: str,
        protected_spans: Sequence[ProtectedSpan],
    ) -> List[ValidationIssue]:
        """
        Executes structural, factual, and semantic checks.
        Returns list of ValidationIssue items.
        """
        issues: List[ValidationIssue] = []

        # 1. Exact Protected Span Equality Check
        for span in protected_spans:
            if span.original not in transformed_text:
                issues.append(
                    ValidationIssue(
                        code=PROTECTED_SPAN_MISMATCH,
                        severity="error",
                        message=f"Protected span '{span.original}' ({span.kind}) is missing from transformed text.",
                    )
                )

        # 2. Number, Unit, and Currency Preservation Check
        if self.strict_numbers:
            orig_numbers = self.extract_numbers(original_text)
            trans_numbers = self.extract_numbers(transformed_text)

            for num in orig_numbers:
                if num not in trans_numbers:
                    issues.append(
                        ValidationIssue(
                            code="NUMERIC_VALUE_ALTERED",
                            severity="error",
                            message=f"Original numeric value '{num}' was altered or dropped during transformation.",
                        )
                    )

        # 3. Negation Preservation Check
        if self.strict_negation:
            orig_neg = self.extract_negation_tokens(original_text)
            trans_neg = self.extract_negation_tokens(transformed_text)

            if sorted(orig_neg) != sorted(trans_neg):
                issues.append(
                    ValidationIssue(
                        code=NEGATION_ALTERED,
                        severity="error",
                        message=(
                            f"Negation language was altered. "
                            f"Original: {orig_neg}, Transformed: {trans_neg}"
                        ),
                    )
                )

        # 4. Modal and Certainty Qualification Drift
        orig_cert, orig_uncert = self.extract_modals(original_text)
        trans_cert, trans_uncert = self.extract_modals(transformed_text)

        if len(orig_cert) != len(trans_cert) or len(orig_uncert) != len(trans_uncert):
            issues.append(
                ValidationIssue(
                    code=SEMANTIC_DRIFT_DETECTED,
                    severity="warning",
                    message=(
                        f"Modal qualification shifts detected. "
                        f"Certainty: {orig_cert} -> {trans_cert}; Uncertainty: {orig_uncert} -> {trans_uncert}"
                    ),
                )
            )

        # 5. Paragraph Count Integrity
        orig_paras = [p for p in original_text.split("\n\n") if p.strip()]
        trans_paras = [p for p in transformed_text.split("\n\n") if p.strip()]
        if len(orig_paras) != len(trans_paras):
            issues.append(
                ValidationIssue(
                    code="PARAGRAPH_COUNT_MISMATCH",
                    severity="warning",
                    message=f"Paragraph count changed from {len(orig_paras)} to {len(trans_paras)}.",
                )
            )

        # 6. Citation Consistency
        if self.strict_citations:
            orig_ieee = len(re.findall(r"\[\d+(?:[,\-–]\s*\d+)*\]", original_text))
            trans_ieee = len(re.findall(r"\[\d+(?:[,\-–]\s*\d+)*\]", transformed_text))
            if orig_ieee != trans_ieee:
                issues.append(
                    ValidationIssue(
                        code="CITATION_COUNT_MISMATCH",
                        severity="error",
                        message=f"IEEE citation count mismatch: {orig_ieee} in original, {trans_ieee} in transformed.",
                    )
                )

        # 7. Directional and Causal Polarity Check
        orig_words = set(re.findall(r"\b[a-zA-Z]+\b", original_text.lower()))
        trans_words = set(re.findall(r"\b[a-zA-Z]+\b", transformed_text.lower()))
        
        orig_pos = orig_words & POSITIVE_DIRECTION_WORDS
        orig_neg = orig_words & NEGATIVE_DIRECTION_WORDS
        trans_pos = trans_words & POSITIVE_DIRECTION_WORDS
        trans_neg = trans_words & NEGATIVE_DIRECTION_WORDS

        # Check if positive direction flipped to negative or vice versa
        if (orig_pos and trans_neg and not trans_pos) or (orig_neg and trans_pos and not trans_neg):
            issues.append(
                ValidationIssue(
                    code="CLAIM_POLARITY_INVERTED",
                    severity="error",
                    message="Directional claim polarity appears inverted between positive and negative findings.",
                )
            )

        # 8. Structural and Residual Artifact Check
        orig_prot_tokens = original_text.count("<<CANOPUS_PROT_")
        trans_prot_tokens = transformed_text.count("<<CANOPUS_PROT_")
        if trans_prot_tokens > orig_prot_tokens or ("\x00" in transformed_text and "\x00" not in original_text):
            issues.append(
                ValidationIssue(
                    code="CORRUPTED_TEXT_ARTIFACT",
                    severity="error",
                    message="Residual placeholder or null byte artifact detected in transformed output.",
                )
            )

        return issues
