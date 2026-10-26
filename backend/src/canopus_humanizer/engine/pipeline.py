"""Stage-based transformation pipeline executing the 8 core architectural stages."""

import time
import uuid
from typing import Optional, Sequence, Tuple

from canopus_humanizer.engine.classifier import DocumentClassification, DocumentClassifier
from canopus_humanizer.engine.diff import generate_unified_diff
from canopus_humanizer.engine.errors import InputError, NUL_BYTE_DETECTED
from canopus_humanizer.engine.models import (
    Change,
    TransformRequest,
    TransformResult,
    ValidationIssue,
)
from canopus_humanizer.engine.normalization import normalize_input_text
from canopus_humanizer.engine.opportunity import OpportunityDetector
from canopus_humanizer.engine.planner import ChangePlanner
from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector, ProtectedSpanRegistry
from canopus_humanizer.engine.providers import DeterministicProvider, EditingProvider
from canopus_humanizer.engine.segmentation import TextSegmenter
from canopus_humanizer.engine.transforms import apply_changes_to_text
from canopus_humanizer.engine.validation import OutputValidator
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.observability.audit import AuditEvent, AuditLogger
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.security.limits import DEFAULT_LIMITS, ResourceLimits


class Pipeline:
    """
    The modular 8-stage text transformation pipeline:
    1. Input validation and normalization.
    2. Document and content-type classification.
    3. Sentence and paragraph segmentation & span protection.
    4. Identification of specific editing opportunities.
    5. Context-aware candidate revision.
    6. Semantic and structural validation.
    7. Acceptance, rejection, or conservative fallback.
    8. Output assembly and change reporting.
    """

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        limits: Optional[ResourceLimits] = None,
        audit_logger: Optional[AuditLogger] = None,
        provider: Optional[EditingProvider] = None,
        version: str = "4.0.0",
    ):
        self.engine_version = version
        self.registry = registry or RuleRegistry()
        self.limits = limits or DEFAULT_LIMITS
        self.audit_logger = audit_logger or AuditLogger()
        self.segmenter = TextSegmenter()
        self.classifier = DocumentClassifier()
        self.opportunity_detector = OpportunityDetector()
        self.provider = provider or DeterministicProvider()
        self.metrics_calculator = TextMetricsCalculator()
        self.validator = OutputValidator()

    def process(self, request: TransformRequest, no_op: bool = False) -> TransformResult:
        """Executes the full modular pipeline stages on the request."""
        req_id = uuid.uuid4().hex[:12]
        start_time = time.perf_counter()
        raw_text = request.text

        # ----------------------------------------------------------------------
        # Stage 1: Input Validation and Normalization
        # ----------------------------------------------------------------------
        normalized_text = normalize_input_text(raw_text, self.limits)

        # ----------------------------------------------------------------------
        # Stage 2: Document and Content-Type Classification
        # ----------------------------------------------------------------------
        classification = self.classifier.classify(normalized_text)

        # ----------------------------------------------------------------------
        # Stage 3: Sentence & Paragraph Segmentation & Protected Span Detection
        # ----------------------------------------------------------------------
        detector = ProtectedSpanDetector(custom_terms=request.custom_protected_terms)
        protected_spans = detector.detect(normalized_text)
        span_registry = ProtectedSpanRegistry(protected_spans)

        # Handle No-Op Mode
        if no_op or (request.mode == "manual_review" and not request.ruleset_ids):
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            metrics = self.metrics_calculator.calculate(raw_text).to_dict()
            metrics["protected_spans_count"] = len(protected_spans)
            metrics["classification"] = {
                "content_type": classification.content_type,
                "confidence": classification.confidence,
                "is_already_clear": classification.is_already_clear,
                "editing_needs": list(classification.editing_needs),
            }

            result = TransformResult(
                original_text=raw_text,
                transformed_text=raw_text,
                changes=(),
                issues=(),
                engine_version=self.engine_version,
                ruleset_versions=self.registry.get_version_info(request.ruleset_ids),
                accepted=True,
                diff="",
                metrics=metrics,
            )

            self.audit_logger.record_event(
                AuditEvent(
                    timestamp=time.time(),
                    request_id=req_id,
                    engine_version=self.engine_version,
                    ruleset_versions=result.ruleset_versions,
                    duration_ms=duration_ms,
                    status="success",
                    input_char_count=len(raw_text),
                    output_char_count=len(raw_text),
                    modifications_count=0,
                    rules_applied=(),
                    issues_count=0,
                )
            )
            return result

        # Mask Protected Spans
        masked_text = span_registry.mask(normalized_text)

        # ----------------------------------------------------------------------
        # Stage 4: Identification of Specific Editing Opportunities
        # ----------------------------------------------------------------------
        enabled_rules = self.registry.get_enabled_rules(request.ruleset_ids)
        opportunities = self.opportunity_detector.detect_opportunities(
            text=masked_text,
            rules=enabled_rules,
            classification=classification,
            mode=request.mode,
        )

        # ----------------------------------------------------------------------
        # Stage 5: Context-Aware Candidate Revision
        # ----------------------------------------------------------------------
        planner = ChangePlanner(max_changes=request.max_changes, mode=request.mode)
        approved_changes, plan_issues = planner.plan(
            text=masked_text,
            rules=enabled_rules,
            protected_spans=protected_spans,
            placeholder_tokens=list(span_registry.placeholder_map.keys()),
            opportunities=opportunities,
        )

        transformed_masked, provider_notes = self.provider.apply_edits(
            text=masked_text,
            changes=approved_changes,
        )

        # ----------------------------------------------------------------------
        # Stage 6: Semantic and Structural Validation & Span Restoration
        # ----------------------------------------------------------------------
        restored_text, restore_ok, restore_errors = span_registry.restore(
            transformed_masked, original_raw_text=raw_text
        )

        all_issues = list(plan_issues)
        for err in restore_errors:
            all_issues.append(
                ValidationIssue(
                    code="PROTECTION_FAILURE",
                    severity="error",
                    message=err,
                )
            )

        final_text = restored_text if restore_ok else raw_text

        # Validate Output & Enforce Factual Safeguards
        val_issues = self.validator.validate(raw_text, final_text, protected_spans)
        all_issues.extend(val_issues)

        # ----------------------------------------------------------------------
        # Stage 7: Acceptance, Rejection, or Conservative Fallback
        # ----------------------------------------------------------------------
        has_critical_error = any(i.severity == "error" for i in all_issues)
        accepted = (restore_ok and not has_critical_error)

        if not accepted:
            # Critical failure or validation error: fail closed to original input
            final_text = raw_text

        # ----------------------------------------------------------------------
        # Stage 8: Output Assembly and Change Reporting
        # ----------------------------------------------------------------------
        diff_str = generate_unified_diff(raw_text, final_text)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = self.metrics_calculator.calculate(final_text).to_dict()
        metrics["protected_spans_count"] = len(protected_spans)
        metrics["latency_ms"] = round(duration_ms, 2)
        metrics["classification"] = {
            "content_type": classification.content_type,
            "confidence": classification.confidence,
            "is_already_clear": classification.is_already_clear,
            "editing_needs": list(classification.editing_needs),
        }
        if provider_notes:
            metrics["provider_notes"] = provider_notes

        rules_applied = tuple([c.rule_id for c in approved_changes]) if accepted else ()
        ruleset_versions = self.registry.get_version_info(request.ruleset_ids)

        result = TransformResult(
            original_text=raw_text,
            transformed_text=final_text,
            changes=approved_changes if accepted else (),
            issues=tuple(all_issues),
            engine_version=self.engine_version,
            ruleset_versions=ruleset_versions,
            accepted=accepted,
            diff=diff_str,
            metrics=metrics,
        )

        self.audit_logger.record_event(
            AuditEvent(
                timestamp=time.time(),
                request_id=req_id,
                engine_version=self.engine_version,
                ruleset_versions=ruleset_versions,
                duration_ms=duration_ms,
                status="success" if accepted else "rejected",
                input_char_count=len(raw_text),
                output_char_count=len(final_text),
                modifications_count=len(result.changes),
                rules_applied=rules_applied,
                issues_count=len(all_issues),
                error_code=all_issues[0].code if (not accepted and all_issues) else None,
            )
        )

        return result
