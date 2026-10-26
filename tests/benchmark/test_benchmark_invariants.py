"""Pytest suite executing benchmark invariants for Canopus Humanizer V4."""

import json
from pathlib import Path
import pytest

from tests.benchmark.benchmark_runner import run_benchmark


@pytest.fixture(scope="module")
def benchmark_results():
    return run_benchmark()


def test_benchmark_all_samples_accepted(benchmark_results):
    for r in benchmark_results["results"]:
        assert r["v4_accepted"] is True, f"Sample {r['id']} failed validation!"


def test_benchmark_preservation_rate_100_percent(benchmark_results):
    for r in benchmark_results["results"]:
        assert r["v4_preservation_rate"] == 1.0, f"Sample {r['id']} dropped protected invariants!"


def test_benchmark_zero_unnecessary_edits_on_clear_text(benchmark_results):
    for r in benchmark_results["results"]:
        if r["category"] == "clear_well_written":
            assert r["v4_unnecessary_edits"] == 0, f"Clear sample {r['id']} had unnecessary edits!"


def test_benchmark_no_banned_corrupted_terms(benchmark_results):
    for r in benchmark_results["results"]:
        assert len(r["v4_banned_terms_detected"]) == 0, f"Sample {r['id']} contained banned terms: {r['v4_banned_terms_detected']}"


def test_benchmark_grammar_and_awkward_corrections_applied(benchmark_results):
    sample = next(r for r in benchmark_results["results"] if r["id"] == "grammar_and_awkward_corrections_05")
    assert sample["v4_transformation_rate"] == 1.0
    assert sample["v4_changes_count"] == 4
