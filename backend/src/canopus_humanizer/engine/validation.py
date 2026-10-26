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

        return issues
