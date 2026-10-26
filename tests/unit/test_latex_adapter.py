"""Unit tests for LaTeX adapter with preamble shielding and brace checks."""

import pytest
from canopus_humanizer.adapters.latex import LatexAdapter
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry


def test_latex_adapter_preamble_preservation():
    latex_doc = (
        r"\documentclass{article}" "\n"
        r"\usepackage{amsmath}" "\n"
        r"\begin{document}" "\n"
        r"Due to the fact that $E=mc^2$, we test equations." "\n"
        r"\end{document}"
    )

    adapter = LatexAdapter()
    registry = RuleRegistry()
    pipeline = Pipeline(registry=registry)

    req = TransformRequest(text="", ruleset_ids=("base",))
    out_latex, res = adapter.transform(latex_doc, pipeline=pipeline, request=req)

    assert r"\documentclass{article}" in out_latex
    assert r"\usepackage{amsmath}" in out_latex
    assert r"\begin{document}" in out_latex
    assert "$E=mc^2$" in out_latex
    assert "Because $E=mc^2$" in out_latex
    assert res.accepted is True


def test_latex_brace_balance_enforcement():
    adapter = LatexAdapter()
    open_b, close_b = adapter._check_brace_balance(r"\textbf{Hello} and {world}")
    assert open_b == 2
    assert close_b == 2
