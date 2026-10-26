"""Evaluation harness comparing Original, Legacy Engine, and Canopus V4 Engine."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure paths
repo_root = Path(__file__).resolve().parent.parent.parent
backend_src = repo_root / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from canopus_humanizer.core.modifier import DocumentModifier
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.rules.registry import RuleRegistry


def run_benchmark(output_path: Optional[Path] = None, save_results: bool = False) -> Dict[str, Any]:
    benchmark_file = Path(__file__).resolve().parent / "benchmark_samples.json"
    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"]
    metrics_calc = TextMetricsCalculator()
    reg = RuleRegistry()
    pipeline_v4 = Pipeline(registry=reg, version="4.2.0")
    modifier_legacy = DocumentModifier(seed=42)

    results = []

    for sample in samples:
        sid = sample["id"]
        cat = sample["category"]
        text = sample["source_text"]
        ruleset_ids = tuple(sample.get("ruleset_ids", ["base", "academic"]))
        invariants = sample.get("expected_invariants", {})
        must_preserve = invariants.get("must_preserve", [])
        must_not_contain = invariants.get("must_not_contain", [])
        must_transform = invariants.get("must_transform", [])
        max_unnecessary = invariants.get("max_unnecessary_changes", 5)

        # Baseline original metrics
        orig_metrics = metrics_calc.calculate(text)

        # 1. Run Legacy Engine
        modifier_legacy.changes_log.clear()
        t0 = time.perf_counter()
        legacy_out = modifier_legacy.modify_document(text)
        t_legacy = (time.perf_counter() - t0) * 1000.0
        legacy_metrics = metrics_calc.calculate(legacy_out)

        # 2. Run V4 Pipeline
        req = TransformRequest(
            text=text,
            mode=sample.get("mode", "conservative"),
            ruleset_ids=ruleset_ids,
        )
        t0 = time.perf_counter()
        v4_res = pipeline_v4.process(req)
        t_v4 = (time.perf_counter() - t0) * 1000.0
        v4_out = v4_res.transformed_text
        v4_metrics = metrics_calc.calculate(v4_out)

        # Evaluate V4 invariants
        preserved_v4 = [token for token in must_preserve if token in v4_out]
        preservation_rate_v4 = (len(preserved_v4) / len(must_preserve)) if must_preserve else 1.0

        banned_in_v4 = [token for token in must_not_contain if token in v4_out]
        transformed_v4 = [token for token in must_transform if token in v4_out]
        transformation_rate_v4 = (len(transformed_v4) / len(must_transform)) if must_transform else 1.0

        # Evaluate Legacy invariants
        preserved_leg = [token for token in must_preserve if token in legacy_out]
        preservation_rate_leg = (len(preserved_leg) / len(must_preserve)) if must_preserve else 1.0
        banned_in_leg = [token for token in must_not_contain if token in legacy_out]

        # Evaluate unnecessary edits for all samples
        if cat == "clear_well_written":
            unnecessary_edits_v4 = len(v4_res.changes)
            unnecessary_edits_legacy = modifier_legacy.total_transforms
        else:
            # Edits beyond targeted flaw transformations for this sample
            targeted_count = len(must_transform)
            unnecessary_edits_v4 = max(0, len(v4_res.changes) - targeted_count)
            unnecessary_edits_legacy = max(0, modifier_legacy.total_transforms - targeted_count)

        sample_eval = {
            "id": sid,
            "category": cat,
            "original_char_count": len(text),
            "v4_accepted": v4_res.accepted,
            "v4_changes_count": len(v4_res.changes),
            "v4_preservation_rate": round(preservation_rate_v4, 3),
            "v4_transformation_rate": round(transformation_rate_v4, 3),
            "v4_banned_terms_detected": banned_in_v4,
            "v4_unnecessary_edits": unnecessary_edits_v4,
            "legacy_unnecessary_edits": unnecessary_edits_legacy,
            "max_unnecessary_changes": max_unnecessary,
            "v4_latency_ms": round(t_v4, 2),
            "legacy_changes_count": modifier_legacy.total_transforms,
            "legacy_preservation_rate": round(preservation_rate_leg, 3),
            "legacy_banned_terms_detected": banned_in_leg,
            "legacy_latency_ms": round(t_legacy, 2),
            "readability": {
                "original_flesch": orig_metrics.flesch_reading_ease,
                "legacy_flesch": legacy_metrics.flesch_reading_ease,
                "v4_flesch": v4_metrics.flesch_reading_ease,
            },
        }
        results.append(sample_eval)

    report = {
        "benchmark_version": data.get("version", "4.2.0"),
        "timestamp": time.time(),
        "total_samples": len(samples),
        "results": results,
    }

    # Save to json file only when requested
    if save_results or output_path is not None:
        target_file = output_path or (Path(__file__).resolve().parent / "benchmark_results.json")
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Canopus Humanizer Benchmark Runner")
    parser.add_argument("--no-save", action="store_true", help="Do not save results to file")
    parser.add_argument("--output", type=Path, default=None, help="Custom output path for results JSON")
    cli_args = parser.parse_args()

    rep = run_benchmark(output_path=cli_args.output, save_results=not cli_args.no_save)
    print("=" * 80)
    print(f"CANOPUS HUMANIZER V4 BENCHMARK REPORT ({rep['total_samples']} Samples)")
    print("=" * 80)
    for r in rep["results"]:
        print(f"\n[{r['id']}] ({r['category']}):")
        print(f"  V4 Status           : {'ACCEPTED' if r['v4_accepted'] else 'REJECTED'}")
        print(f"  V4 Preservation     : {r['v4_preservation_rate'] * 100:.1f}%")
        print(f"  V4 Transformation   : {r['v4_transformation_rate'] * 100:.1f}%")
        print(f"  V4 Changes / Legacy : {r['v4_changes_count']} changes vs {r['legacy_changes_count']} changes")
        print(f"  V4 Unnecessary Edits: {r['v4_unnecessary_edits']} (Max Allowed: {r['max_unnecessary_changes']})")
        print(f"  V4 Banned Terms     : {r['v4_banned_terms_detected'] or 'None'}")
        print(f"  Legacy Banned Terms : {r['legacy_banned_terms_detected'] or 'None'}")
        print(f"  Flesch Reading Ease : Original={r['readability']['original_flesch']}, V4={r['readability']['v4_flesch']}")
        print(f"  Latency             : V4={r['v4_latency_ms']}ms, Legacy={r['legacy_latency_ms']}ms")
