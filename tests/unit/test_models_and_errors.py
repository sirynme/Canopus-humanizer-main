"""Unit tests for Canopus data models and error hierarchy."""

import pytest
from canopus_humanizer.engine.errors import (
    CanopusError,
    InputError,
    FormatError,
    RulesetError,
    ProtectionError,
    ValidationError,
    SecurityError,
    ResourceError,
    INPUT_INVALID,
    RULESET_INVALID,
)
from canopus_humanizer.engine.models import (
    Change,
    DocumentBlock,
    DocumentModel,
    ProtectedSpan,
    TransformRequest,
    TransformResult,
    ValidationIssue,
)


def test_canopus_humanizer_error_hierarchy():
    err = CanopusError("General engine failure", code="GENERAL_ERROR", details={"key": "val"})
    assert str(err) == "[GENERAL_ERROR] General engine failure"
    d = err.to_dict()
    assert d["error"] == "CanopusError"
    assert d["code"] == "GENERAL_ERROR"
    assert d["details"]["key"] == "val"

    sub_err = InputError("Invalid input text", code=INPUT_INVALID)
    assert isinstance(sub_err, CanopusError)
    assert sub_err.code == INPUT_INVALID


def test_transform_request_defaults():
    req = TransformRequest(text="Sample test text.")
    assert req.text == "Sample test text."
    assert req.mode == "conservative"
    assert req.ruleset_ids == ("base",)
    assert req.preserve_citations is True
    assert req.preserve_numbers is True
    assert req.max_changes == 500


def test_transform_result_immutability():
    change = Change(
        rule_id="r1",
        start=0,
        end=5,
        before="Hello",
        after="Greetings",
        category="style",
        requires_review=False,
    )
    issue = ValidationIssue(
        code="TEST_ISSUE",
        severity="info",
        message="Informational note",
    )
    res = TransformResult(
        original_text="Hello world",
        transformed_text="Greetings world",
        changes=(change,),
        issues=(issue,),
        engine_version="1.0.0",
        ruleset_versions=("base@1.0.0:abc",),
        accepted=True,
    )

    assert res.accepted is True
    assert len(res.changes) == 1
    assert res.changes[0].after == "Greetings"
    assert len(res.issues) == 1

    # Verify frozen immutability
    with pytest.raises(AttributeError):
        res.accepted = False


def test_document_model_blocks():
    block1 = DocumentBlock(
        block_id="p1",
        block_type="paragraph",
        start=0,
        end=10,
        content="Paragraph1",
    )
    model = DocumentModel(
        blocks=(block1,),
        format_name="plain_text",
    )
    assert len(model.blocks) == 1
    assert model.blocks[0].content == "Paragraph1"
    assert model.format_name == "plain_text"
