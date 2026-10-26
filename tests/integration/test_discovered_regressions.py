"""Regression test suite covering actual defects discovered and resolved during implementation."""

import re
import pytest
from pathlib import Path

from canopus_humanizer.engine.protected_spans import ProtectedSpanDetector
from canopus_humanizer.engine.errors import OUTPUT_VALIDATION_FAILED
from canopus_humanizer.adapters.plain_text import PlainTextAdapter
from canopus_humanizer.adapters.latex import LatexAdapter


def test_regression_pyproject_author_email_format():
    """
    Regression Test: In the previous configuration, project.authors[0].email had value
    'canopus-humanizer@local', which caused setuptools/validate-pyproject to crash during
    'pip install -e .' with:
        'configuration error: `project.authors[0].email` must be idn-email'.
    This test verifies pyproject.toml has a compliant idn-email format.
    """
    pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'email\s*=\s*"([^"]+)"', content)
    assert match is not None
    email = match.group(1)
    # Must have a standard top-level domain compliant with idn-email
    assert "@" in email and "." in email.split("@")[-1]
    assert not email.endswith(".local")


def test_regression_latex_error_import_symbol():
    """
    Regression Test: latex.py previously attempted to import VALIDATION_FAILED
    instead of OUTPUT_VALIDATION_FAILED from canopus_humanizer.engine.errors, crashing on load.
    This test verifies that LatexAdapter imports cleanly and exports correct symbol.
    """
    adapter = LatexAdapter()
    assert adapter.format_name == "latex"
    assert OUTPUT_VALIDATION_FAILED == "OUTPUT_VALIDATION_FAILED"


def test_regression_plain_text_optional_typing_import():
    """
    Regression Test: plain_text.py previously omitted Optional from typing imports,
    which triggered NameError when type hints evaluated.
    """
    adapter = PlainTextAdapter()
    assert adapter.format_name == "plain_text"


def test_regression_dollar_math_vs_currency_distinction():
    """
    Regression Test: Naive regex for inline math '$...$' captured dollar amounts such as
    '$25.00' or '$4.5 million', mangling currency formatting.
    This test verifies that currency expressions are never misclassified as inline math.
    """
    detector = ProtectedSpanDetector()
    text = "The price was $25.00 and the funding was $4.5 million, whereas $x + y = z$ is math."
    spans = detector.detect(text)

    span_dict = {s.original: s.kind for s in spans}
    assert span_dict["$25.00"] == "currency"
    assert span_dict["$4.5 million"] == "currency"
    assert span_dict["$x + y = z$"] == "math_inline"


def test_regression_transforms_sequence_typing_import():
    """
    Regression Test: backend/src/canopus_humanizer/engine/transforms.py previously omitted
    Sequence from typing import, raising NameError: name 'Sequence' is not defined when
    type hints are inspected or evaluated at runtime.
    """
    from typing import get_type_hints
    from canopus_humanizer.engine.transforms import apply_changes_to_text
    hints = get_type_hints(apply_changes_to_text)
    assert "changes" in hints
    assert "Sequence" in str(hints["changes"])


def test_regression_legacy_rules_directory_discovery():
    """
    Regression Test: The legacy rules loader previously resolved candidate paths by checking
    if candidate.is_dir(). Because backend/src/canopus_humanizer/rules is a Python package
    directory, it falsely matched, leaving SYNONYMS and PHRASES empty.
    This test verifies that rules-directory discovery checks for actual rule JSON files
    and loads the assets from backend/rules.
    """
    from canopus_humanizer.core import rules
    rules_dir = rules.get_rules_dir()
    assert (rules_dir / "synonyms.json").is_file()
    assert (rules_dir / "phrases.json").is_file()
    # Confirm it did NOT match the Python package directory
    assert "backend/src/canopus_humanizer/rules" not in str(rules_dir)
    assert rules.are_rules_loaded()
    assert len(rules.SYNONYMS) > 50
    assert len(rules.PHRASES) > 20


def test_regression_legacy_humanize_applies_modifications():
    """
    Regression Test: Proves that the legacy /v1/humanize endpoint loads its rules
    and applies an expected modification to an appropriate test input.
    """
    from fastapi.testclient import TestClient
    from canopus_humanizer.api.routes import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    input_text = "In order to evaluate the framework, this research paper was conducted."
    resp = client.post(
        "/v1/humanize",
        json={
            "text": input_text,
            "seed": 42,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["telemetry"]["rules_loaded"] is True
    assert data["modifications_count"] >= 1
    assert data["humanized_text"] != input_text
    # "In order to" should be transformed to "To" or "this research paper" to "the present work"
    assert "To evaluate" in data["humanized_text"] or "present work" in data["humanized_text"]


def test_regression_rules_loading_failure_produces_warning(tmp_path):
    """
    Regression Test: Ensures failures to load rules produce an explicit error or warning
    instead of silently returning unchanged input.
    """
    import os
    import warnings
    from canopus_humanizer.core import rules
    from canopus_humanizer.core.modifier import DocumentModifier

    empty_dir = tmp_path / "empty_rules"
    empty_dir.mkdir()

    # When pointing to an empty rules dir, get_rules_dir warns about missing rules
    old_env = os.environ.get("CANOPUS_RULES_DIR")
    try:
        os.environ["CANOPUS_RULES_DIR"] = str(empty_dir)
        with pytest.warns(UserWarning) as warning_records:
            rules.load_json_rule("non_existent_rule_file.json")
        assert any("not found in rules directory" in str(w.message) for w in warning_records)

        # DocumentModifier must emit a RuntimeWarning if rules are empty
        orig_synonyms = dict(rules.SYNONYMS)
        orig_phrases = list(rules.PHRASES)
        try:
            rules.SYNONYMS.clear()
            rules.PHRASES.clear()
            dm = DocumentModifier()
            with pytest.warns(RuntimeWarning) as mod_warnings:
                res = dm.modify_document("In order to evaluate the framework.")
            assert res == "In order to evaluate the framework."
            assert any("Legacy rules failed to load" in str(w.message) for w in mod_warnings)
        finally:
            rules.SYNONYMS.update(orig_synonyms)
            rules.PHRASES.extend(orig_phrases)
    finally:
        if old_env is not None:
            os.environ["CANOPUS_RULES_DIR"] = old_env
        else:
            os.environ.pop("CANOPUS_RULES_DIR", None)

