"""Unit tests verifying each of the 8 explicit transformation pipeline stages."""

import pytest
from canopus_humanizer.engine.classifier import DocumentClassifier
from canopus_humanizer.engine.normalization import normalize_input_text
from canopus_humanizer.engine.opportunity import OpportunityDetector
from canopus_humanizer.engine.models import Change, TransformRequest
from canopus_humanizer.engine.planner import ChangePlanner
from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector, ProtectedSpanRegistry
from canopus_humanizer.engine.providers import DeterministicProvider, OptionalModelProvider
from canopus_humanizer.engine.segmentation import TextSegmenter
from canopus_humanizer.engine.validation import OutputValidator
from canopus_humanizer.rules.registry import RuleRegistry
from canopus_humanizer.rules.schema import RuleDefinition


def test_stage_1_normalization():
    """Stage 1: Normalization strips zero-width chars and composes unicode."""
    dirty = "Hello\u200bWorld\uFEFF\tGood day"
    clean = normalize_input_text(dirty)
    assert clean == "HelloWorld\tGood day"


def test_stage_2_document_classification():
    """Stage 2: Correctly identifies academic vs technical vs general documents."""
    classifier = DocumentClassifier()

    academic_sample = "In this paper, our hypothesis is evaluated on prior investigations (Smith et al., 2024)."
    res_acad = classifier.classify(academic_sample)
    assert res_acad.content_type == "academic"
    assert "has_citations" in res_acad.features and res_acad.features["has_citations"] is True

    tech_sample = "The algorithm runs in $O(n \\log n)$ time with a learning rate of $10^{-4}$ on GPU."
    res_tech = classifier.classify(tech_sample)
    assert res_tech.content_type == "technical"

    clean_sample = "We present a linear-time algorithm for cycle detection in directed graphs."
    res_clean = classifier.classify(clean_sample)
    assert res_clean.is_already_clear is True


def test_stage_3_segmentation_with_offsets():
    """Stage 3: Paragraph and sentence segmentation preserves source offsets."""
    segmenter = TextSegmenter()
    doc = "First sentence here. Second sentence follows.\n\nParagraph two starts here."
    seg_doc = segmenter.segment_document(doc)
    assert len(seg_doc) == 2  # 2 paragraphs
    para1, sents1 = seg_doc[0]
    assert len(sents1) == 2
    assert sents1[0].text == "First sentence here."
    assert sents1[1].text == "Second sentence follows."


def test_stage_4_opportunity_detection():
    """Stage 4: Detects concrete editing opportunities and suppresses stylistic churn on clear text."""
    detector = OpportunityDetector()
    classifier = DocumentClassifier()

    rule = RuleDefinition(
        id="style.test_churn",
        enabled=True,
        category="style",
        risk="medium",
        operation="replace_exact",
        pattern="algorithm",
        replacement="computational procedure",
    )

    clean_text = "The algorithm operates efficiently."
    classif_clear = classifier.classify(clean_text)

    # In conservative mode on clear text, medium-risk stylistic rule is suppressed
    opps = detector.detect_opportunities(clean_text, [("test", rule)], classif_clear, mode="conservative")
    assert len(opps) == 0


def test_stage_5_provider_fallback():
    """Stage 5: Optional model provider gracefully falls back to deterministic provider."""
    # Configured with unreachable endpoint and disabled flag
    provider = OptionalModelProvider(endpoint_url="http://unreachable.local", enabled=False)
    changes = [
        Change(
            rule_id="r1",
            start=0,
            end=3,
            before="Foo",
            after="Bar",
            category="clarity",
            requires_review=False,
        )
    ]
    out, notes = provider.apply_edits("Foo Baz", changes)
    assert out == "Bar Baz"


def test_stage_6_fail_closed_validation():
    """Stage 6: Output validator flags critical errors for rollbacks."""
    validator = OutputValidator()
    # Dropped numeric token
    issues = validator.validate("Accuracy was 98.6%.", "Accuracy was altered.", [])
    assert any(i.code == "NUMERIC_VALUE_ALTERED" and i.severity == "error" for i in issues)
