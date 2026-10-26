"""Unit tests for language-aware source-code comment adapter."""

import pytest
from canopus_humanizer.adapters.code_comments import CodeCommentAdapter
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry


def test_python_comment_transformation_leaves_code_intact():
    code = (
        'def compute():\n'
        '    # Due to the fact that x is positive, we return 1\n'
        '    msg = "This string has # not a comment inside"\n'
        '    return 1\n'
    )

    adapter = CodeCommentAdapter()
    registry = RuleRegistry()
    pipeline = Pipeline(registry=registry)

    req = TransformRequest(text="", ruleset_ids=("base",))
    out_code, res = adapter.transform(code, pipeline=pipeline, language="python", request=req)

    # Comment was transformed
    assert "Because x is positive" in out_code
    # String literal was completely untouched
    assert 'msg = "This string has # not a comment inside"' in out_code
    # Python code syntax is 100% valid
    assert "def compute():" in out_code
    assert "return 1" in out_code
    assert res.accepted is True


def test_c_style_comment_transformation():
    c_code = (
        'int main() {\n'
        '    // In order to exit cleanly\n'
        '    return 0;\n'
        '}\n'
    )

    adapter = CodeCommentAdapter()
    registry = RuleRegistry()
    pipeline = Pipeline(registry=registry)

    req = TransformRequest(text="", ruleset_ids=("base",))
    out_code, res = adapter.transform(c_code, pipeline=pipeline, language="c", request=req)

    assert "// To exit cleanly" in out_code
    assert "return 0;" in out_code
    assert res.accepted is True
