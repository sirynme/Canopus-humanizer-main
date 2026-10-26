"""Deterministic transformation pipeline executing the 10 core architectural stages."""

import time
import uuid
from typing import Optional, Tuple

from canopus_humanizer.engine.diff import generate_unified_diff
from canopus_humanizer.engine.errors import (
    InputError,
    NUL_BYTE_DETECTED,
    CanopusError,
)
from canopus_humanizer.engine.models import (
    Change,
    TransformRequest,
    TransformResult,
    ValidationIssue,
)
from canopus_humanizer.engine.planner import ChangePlanner
from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector, ProtectedSpanRegistry
from canopus_humanizer.engine.segmentation import TextSegmenter
from canopus_humanizer.engine.transforms import apply_changes_to_text
from canopus_humanizer.engine.validation import OutputValidator
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.observability.audit import AuditEvent, AuditLogger
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.security.limits import DEFAULT_LIMITS, ResourceLimits, validate_input_limits


class Pipeline:
    """The 10-stage deterministic text transformation pipeline."""

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        limits: Optional[ResourceLimits] = None,
        audit_logger: Optional[AuditLogger] = None,
        version: str = "1.0.0",
    ):
        self.engine_version = version
        self.registry = registry or RuleRegistry()
        self.limits = limits or DEFAULT_LIMITS
        self.audit_logger = audit_logger or AuditLogger()
        self.segmenter = TextSegmenter()
        self.metrics_calculator = TextMetricsCalculator()
        self.validator = OutputValidator()

    def process(self, request: TransformRequest, no_op: bool = False) -> TransformResult:
        """Executes the full pipeline stages on the request."""
        req_id = uuid.uuid4().hex[:12]
        start_time = time.perf_counter()
        original_text = request.text

        # Stage 1: Input Validation and Normalization
        validate_input_limits(original_text, self.limits)
        if "\x00" in original_text:
            raise InputError("Input text contains prohibited NUL bytes", code=NUL_BYTE_DETECTED)

        # Stage 2: Detect Protected Spans
        detector = ProtectedSpanDetector(custom_terms=request.custom_protected_terms)
        protected_spans = detector.detect(original_text)
        span_registry = ProtectedSpanRegistry(protected_spans)

        # Handle No-Op Mode (returns original text with validation and metrics)
        if no_op or request.mode == "manual_review" and not request.ruleset_ids:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            metrics = self.metrics_calculator.calculate(original_text).to_dict()
            metrics["protected_spans_count"] = len(protected_spans)

            result = TransformResult(
                original_text=original_text,
                transformed_text=original_text,
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
                    input_char_count=len(original_text),
                    output_char_count=len(original_text),
                    modifications_count=0,
                    rules_applied=(),
                    issues_count=0,
                )
            )
            return result

        # Stage 3: Mask Protected Spans
        masked_text = span_registry.mask(original_text)

        # Stage 4: Retrieve Rules & Plan Deterministic Changes
        enabled_rules = self.registry.get_enabled_rules(request.ruleset_ids)
        planner = ChangePlanner(max_changes=request.max_changes, mode=request.mode)
        approved_changes, plan_issues = planner.plan(
            text=masked_text,
            rules=enabled_rules,
            protected_spans=protected_spans,
            placeholder_tokens=list(span_registry.placeholder_map.keys()),
        )

        # Stage 5: Apply Approved Edits in Reverse Offset Order
        transformed_masked = apply_changes_to_text(masked_text, approved_changes)

        # Stage 6: Restore Protected Spans with Fail-Closed Verification
        restored_text, restore_ok, restore_errors = span_registry.restore(
            transformed_masked, original_raw_text=original_text
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

        if not restore_ok:
            # Critical failure: roll back to original text immediately
            final_text = original_text
        else:
            final_text = restored_text

        # Stage 7: Validate Output & Enforce Factual Safeguards
        val_issues = self.validator.validate(original_text, final_text, protected_spans)
        all_issues.extend(val_issues)

        has_critical_error = any(i.severity == "error" for i in all_issues)
        accepted = (restore_ok and not has_critical_error)

        if not accepted and restore_ok:
            # Fail closed on validation error: revert to original text
            final_text = original_text

        # Stage 8: Produce Unified Diff
        diff_str = generate_unified_diff(original_text, final_text)

        # Stage 9: Calculate Metrics & Acceptance
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = self.metrics_calculator.calculate(final_text).to_dict()
        metrics["protected_spans_count"] = len(protected_spans)
        metrics["latency_ms"] = round(duration_ms, 2)

        rules_applied = tuple([c.rule_id for c in approved_changes]) if accepted else ()
        ruleset_versions = self.registry.get_version_info(request.ruleset_ids)

        result = TransformResult(
            original_text=original_text,
            transformed_text=final_text,
            changes=approved_changes if accepted else (),
            issues=tuple(all_issues),
            engine_version=self.engine_version,
            ruleset_versions=ruleset_versions,
            accepted=accepted,
            diff=diff_str,
            metrics=metrics,
        )

        # Stage 10: Audit Event Logging
        self.audit_logger.record_event(
            AuditEvent(
                timestamp=time.time(),
                request_id=req_id,
                engine_version=self.engine_version,
                ruleset_versions=ruleset_versions,
                duration_ms=duration_ms,
                status="success" if accepted else "rejected",
                input_char_count=len(original_text),
                output_char_count=len(final_text),
                modifications_count=len(result.changes),
                rules_applied=rules_applied,
                issues_count=len(all_issues),
                error_code=all_issues[0].code if (not accepted and all_issues) else None,
            )
        )

        return result
