#!/usr/bin/env python3
"""Local user-style evaluation for Canopus V4; external detectors are separate."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.rules.registry import RuleRegistry
from run_api import app

SAMPLE_PATH = Path(__file__).with_name("ai_user_samples.json")
OUT_PATH = Path(__file__).with_name("ai_user_evaluation_results.json")

RULESETS = {
    "general": ["base", "grammar"],
    "academic": ["base", "academic", "grammar"],
    "technical": ["base", "academic", "technical", "grammar"],
}


def check_case(sample: dict, pipeline: Pipeline, client: TestClient) -> dict:
    text = sample["text"]
    rulesets = tuple(RULESETS[sample["domain"]])
    request = TransformRequest(text=text, ruleset_ids=rulesets)
    result = pipeline.process(request)
    second = pipeline.process(TransformRequest(text=result.transformed_text, ruleset_ids=rulesets))
    response = client.post("/v1/transform", json={
        "text": text,
        "ruleset_ids": list(rulesets),
        "mode": "conservative",
    })
    api = response.json()
    legacy_response = client.post("/v1/humanize", json={
        "text": text,
        "seed": 42,
        "style": sample["domain"],
    })
    legacy = legacy_response.json()
    offsets_valid = all(text[c.start:c.end] == c.before for c in result.changes)
    return {
        "id": sample["id"],
        "level": sample["level"],
        "domain": sample["domain"],
        "input_words": len(text.split()),
        "input_characters": len(text),
        "accepted": result.accepted,
        "change_count": len(result.changes),
        "changes": [c.__dict__ for c in result.changes],
        "issues": [i.__dict__ for i in result.issues],
        "original_text": text,
        "transformed_text": result.transformed_text,
        "metrics_before": TextMetricsCalculator().calculate(text).to_dict(),
        "metrics_after": result.metrics,
        "legacy_endpoint": {
            "status_code": legacy_response.status_code,
            "success": legacy.get("success") is True,
            "modifications_count": legacy.get("modifications_count"),
            "output": legacy.get("humanized_text", ""),
        },
        "checks": {
            "api_status_200": response.status_code == 200,
            "api_accepted": api.get("accepted") is True,
            "output_matches_api": api.get("transformed_text") == result.transformed_text,
            "offsets_reference_original": offsets_valid,
            "idempotent": second.accepted and second.transformed_text == result.transformed_text and not second.changes,
            "meaning_safeguards_have_no_errors": not any(i.severity == "error" for i in result.issues),
        },
        "output_changed": result.transformed_text != text,
    }


def main() -> None:
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    pipeline = Pipeline(registry=RuleRegistry(), version="4.2.0")
    client = TestClient(app)
    results = [check_case(sample, pipeline, client) for sample in data["samples"]]
    report = {
        "version": "1.0",
        "source": str(SAMPLE_PATH),
        "engine": "Canopus V4 /v1/transform",
        "detectors": "external detector checks are recorded separately",
        "results": results,
        "all_local_checks_pass": all(all(r["checks"].values()) for r in results),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "all_local_checks_pass": report["all_local_checks_pass"],
        "samples": [{"id": r["id"], "words": r["input_words"], "changes": r["change_count"], "accepted": r["accepted"], "checks": r["checks"]} for r in results],
    }, indent=2))

if __name__ == "__main__":
    main()
