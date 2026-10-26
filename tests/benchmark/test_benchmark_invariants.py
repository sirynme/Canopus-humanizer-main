"""Pytest suite executing benchmark invariants for Canopus Humanizer V4."""

import json
from pathlib import Path
import pytest

from tests.benchmark.benchmark_runner import run_benchmark


@pytest.fixture(scope="module")
def benchmark_results():
    """Executes benchmark invariants purely in-memory without modifying tracked results files."""
    return run_benchmark(save_results=False)


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


def test_benchmark_max_unnecessary_changes_budget(benchmark_results):
    """Evaluates that unnecessary edits across all samples do not exceed configured limits."""
    for r in benchmark_results["results"]:
        max_allowed = r.get("max_unnecessary_changes", 5)
        assert r["v4_unnecessary_edits"] <= max_allowed, (
            f"Sample {r['id']} had {r['v4_unnecessary_edits']} unnecessary edits, "
            f"exceeding max budget of {max_allowed}!"
        )


def test_benchmark_invariants_do_not_modify_tracked_results_file():
    """Verifies that running benchmark invariants leaves committed results file completely untouched."""
    committed_path = Path(__file__).resolve().parent / "benchmark_results.json"
    if not committed_path.exists():
        return

    mtime_before = committed_path.stat().st_mtime_ns
    content_before = committed_path.read_bytes()

    res = run_benchmark(save_results=False)
    assert len(res["results"]) == 10

    mtime_after = committed_path.stat().st_mtime_ns
    content_after = committed_path.read_bytes()

    assert mtime_before == mtime_after, "benchmark_results.json mtime was modified during test!"
    assert content_before == content_after, "benchmark_results.json bytes were modified during test!"


def test_benchmark_fresh_execution_matches_committed_results(benchmark_results):
    """Compares in-memory benchmark metrics against committed results, strictly validating invariants while allowing timing variations."""
    committed_path = Path(__file__).resolve().parent / "benchmark_results.json"
    if not committed_path.exists():
        pytest.skip("benchmark_results.json not found")

    with open(committed_path, "r", encoding="utf-8") as f:
        committed = json.load(f)

    assert benchmark_results["total_samples"] == committed["total_samples"]
    assert benchmark_results["benchmark_version"] == committed["benchmark_version"]

    committed_map = {r["id"]: r for r in committed["results"]}
    for fresh in benchmark_results["results"]:
        sid = fresh["id"]
        assert sid in committed_map, f"Missing {sid} in committed benchmark results"
        comm = committed_map[sid]

        assert fresh["v4_accepted"] == comm["v4_accepted"]
        assert fresh["v4_changes_count"] == comm["v4_changes_count"]
        assert fresh["v4_preservation_rate"] == comm["v4_preservation_rate"]
        assert fresh["v4_transformation_rate"] == comm["v4_transformation_rate"]
        assert fresh["v4_unnecessary_edits"] == comm["v4_unnecessary_edits"]
        assert fresh["v4_banned_terms_detected"] == comm["v4_banned_terms_detected"]
        assert fresh["legacy_changes_count"] == comm["legacy_changes_count"]
        assert fresh["legacy_preservation_rate"] == comm["legacy_preservation_rate"]
        assert fresh["legacy_banned_terms_detected"] == comm["legacy_banned_terms_detected"]
        assert fresh["readability"]["original_flesch"] == comm["readability"]["original_flesch"]
        assert fresh["readability"]["v4_flesch"] == comm["readability"]["v4_flesch"]
