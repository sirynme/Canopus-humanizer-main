"""FastAPI router implementation for canopus-humanizer and Canopus Core Engine."""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from canopus_humanizer.api.schemas import (
    CitationFormatRequest,
    CitationFormatResponse,
    HealthResponse,
    HumanizeRequest,
    HumanizeResponse,
    TransformApiRequest,
    TransformApiResponse,
    TransformChangeSchema,
    ValidationIssueSchema,
)
from canopus_humanizer.config import GLOBAL_CONFIG, ConfigNamespace
from canopus_humanizer.core.modifier import DocumentModifier

from canopus_humanizer.citations.formatters import CitationFormatter
from canopus_humanizer.citations.validation import CitationValidator
from canopus_humanizer.engine.models import TransformRequest as EngineRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.rules.registry import RuleRegistry


router = APIRouter(prefix="/v1", tags=["Humanizer & Canopus Engine"])

_default_registry = RuleRegistry()
_default_pipeline = Pipeline(registry=_default_registry, version="4.2.0")
_metrics_calculator = TextMetricsCalculator()
_citation_validator = CitationValidator()
_citation_formatter = CitationFormatter()


@router.post("/transform", response_model=TransformApiResponse)
async def transform_endpoint(payload: TransformApiRequest) -> TransformApiResponse:
    """Full Canopus deterministic transformation pipeline with diff and audit metrics."""
    req = EngineRequest(
        text=payload.text,
        mode=payload.mode,
        ruleset_ids=tuple(payload.ruleset_ids),
        custom_protected_terms=tuple(payload.custom_protected_terms),
        max_changes=payload.max_changes,
        preserve_citations=payload.preserve_citations,
        preserve_numbers=payload.preserve_numbers,
    )
    result = _default_pipeline.process(req, no_op=payload.no_op)

    changes = [
        TransformChangeSchema(
            rule_id=c.rule_id,
            start=c.start,
            end=c.end,
            before=c.before,
            after=c.after,
            category=c.category,
            requires_review=c.requires_review,
        )
        for c in result.changes
    ]

    issues = [
        ValidationIssueSchema(
            code=i.code,
            severity=i.severity,
            message=i.message,
            start=i.start,
            end=i.end,
        )
        for i in result.issues
    ]

    return TransformApiResponse(
        accepted=result.accepted,
        original_text=result.original_text,
        transformed_text=result.transformed_text,
        changes=changes,
        issues=issues,
        engine_version=result.engine_version,
        ruleset_versions=list(result.ruleset_versions),
        diff=result.diff,
        metrics=result.metrics,
    )


@router.get("/rulesets")
async def list_rulesets_endpoint() -> Dict[str, Any]:
    """Lists all loaded and validated rule packs with versions and hashes."""
    ruleset_info = {}
    for r_id, rs in _default_registry._rulesets.items():
        ruleset_info[r_id] = {
            "ruleset_id": rs.ruleset_id,
            "version": rs.version,
            "language": rs.language,
            "rules_count": len(rs.rules),
            "content_hash": rs.content_hash,
        }
    return {"rulesets": ruleset_info}


@router.post("/citations/format", response_model=CitationFormatResponse)
async def format_citation_endpoint(payload: CitationFormatRequest) -> CitationFormatResponse:
    """Formats reference metadata into APA, IEEE, and BibTeX styles."""
    data = payload.model_dump()
    meta = _citation_validator.validate_metadata(data)

    apa_str = _citation_formatter.format_apa(data)
    ieee_str = _citation_formatter.format_ieee(data)
    bibtex_str = _citation_formatter.format_bibtex(data)

    return CitationFormatResponse(
        apa=apa_str,
        ieee=ieee_str,
        bibtex=bibtex_str,
        status=meta.status,
        validation_notes=list(meta.validation_notes),
    )


@router.post("/humanize", response_model=HumanizeResponse)
async def humanize_endpoint(payload: HumanizeRequest) -> HumanizeResponse:
    """Legacy endpoint supporting existing UI and backward compatibility."""
    start_time = time.perf_counter()

    req_config = ConfigNamespace()
    req_config.INTENSITY = payload.intensity if payload.intensity is not None else 70.0
    req_config.STYLE = payload.style or "academic"
    if payload.enable_synonyms is not None:
        req_config.ENABLE_SYNONYMS = payload.enable_synonyms
    if payload.enable_phrase_rewrite is not None:
        req_config.ENABLE_PHRASE_REWRITE = payload.enable_phrase_rewrite
    if payload.enable_determiner_swap is not None:
        req_config.ENABLE_DETERMINER_SWAP = payload.enable_determiner_swap
    if payload.enable_discourse_rotate is not None:
        req_config.ENABLE_DISCOURSE_ROTATE = payload.enable_discourse_rotate
    if payload.enable_sentence_fusion is not None:
        req_config.ENABLE_SENTENCE_FUSION = payload.enable_sentence_fusion

    modifier = DocumentModifier(config=req_config, seed=payload.seed)
    protected_set = set(payload.protected_terms or [])

    from canopus_humanizer.core.rules import are_rules_loaded
    rules_ok = are_rules_loaded()
    if not rules_ok:
        import warnings
        warnings.warn(
            "Legacy rules failed to load. /v1/humanize will return unchanged input.",
            RuntimeWarning,
            stacklevel=2,
        )

    humanized = modifier.modify_document(
        payload.text,
        protected_terms=protected_set,
        enable_citations=False,
    )

    latency = round((time.perf_counter() - start_time) * 1000.0, 2)
    words = len(payload.text.split())

    telemetry: Dict[str, Any] = {
        "rules_loaded": rules_ok,
        "total_modifications": modifier.total_transforms,
        "word_count": words,
        "stages_applied": [
            k for k, v in {
                "phrase_rewrite": modifier.phrase_rewrite_count,
                "synonyms": modifier.synonym_count,
                "determiner_swap": modifier.determiner_swap_count,
                "discourse_rotation": modifier.discourse_rotate_count,
                "sentence_fusion": modifier.sentence_fusion_count,
            }.items() if v > 0
        ],
    }
    if not rules_ok:
        telemetry["warning"] = "Legacy rules failed to load; input returned unchanged."

    return HumanizeResponse(
        success=True,
        humanized_text=humanized,
        words_processed=words,
        modifications_count=modifier.total_transforms,
        latency_ms=latency,
        telemetry=telemetry,
    )


@router.get("/health", response_model=HealthResponse)
async def health_endpoint() -> HealthResponse:
    """Service health and liveness probe."""
    return HealthResponse(
        status="healthy",
        engine="canopus-humanizer",
        version=GLOBAL_CONFIG.VERSION,
        timestamp=time.time(),
    )
