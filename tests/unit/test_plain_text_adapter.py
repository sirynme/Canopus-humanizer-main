"""Unit tests for plain text adapter."""

import pytest
from canopus_humanizer.adapters.plain_text import PlainTextAdapter
from canopus_humanizer.engine.errors import InputError
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry


def test_plain_text_adapter_parse_valid():
    adapter = PlainTextAdapter()
    text = "Paragraph one.\n\nParagraph two."
    model = adapter.parse(text)
    assert len(model.blocks) == 2
    assert model.blocks[0].content == "Paragraph one."
    assert model.blocks[1].content == "Paragraph two."


def test_plain_text_adapter_nul_byte_rejection():
    adapter = PlainTextAdapter()
    with pytest.raises(InputError) as exc_info:
        adapter.parse("Text with \x00 nul byte.")
    assert exc_info.value.code == "NUL_BYTE_DETECTED"


def test_plain_text_adapter_no_op_mode():
    registry = RuleRegistry()
    pipeline = Pipeline(registry=registry)
    adapter = PlainTextAdapter()

    text = "Due to the fact that tests pass, we proceed."
    out_text, res = adapter.transform(text, pipeline=pipeline, no_op=True)

    assert out_text == text
    assert len(res.changes) == 0
    assert res.accepted is True
    assert res.diff == ""
