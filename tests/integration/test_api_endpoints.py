"""Integration tests for FastAPI endpoints."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend paths are on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(backend_dir / "src") not in sys.path:
    sys.path.insert(0, str(backend_dir / "src"))

from run_api import app


@pytest.fixture
def api_client():
    return TestClient(app)


def test_api_health(api_client):
    resp = api_client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_rulesets(api_client):
    resp = api_client.get("/v1/rulesets")
    assert resp.status_code == 200
    data = resp.json()
    assert "rulesets" in data
    assert "base" in data["rulesets"]


def test_api_transform(api_client):
    resp = api_client.post(
        "/v1/transform",
        json={
            "text": "Due to the fact that tests are run at 98.6% [1], we succeed.",
            "ruleset_ids": ["base"],
            "mode": "conservative",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] is True
    assert "Because tests are run at 98.6% [1], we succeed." in data["transformed_text"]
    assert len(data["changes"]) == 1
    assert data["changes"][0]["before"] == "Due to the fact that"
    assert data["changes"][0]["after"] == "Because"
    assert "diff" in data
    assert "metrics" in data


def test_api_citation_format(api_client):
    resp = api_client.post(
        "/v1/citations/format",
        json={
            "title": "Deep Learning",
            "authors": ["Goodfellow, I.", "Bengio, Y."],
            "year": "2016",
            "doi": "10.1000/182",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Goodfellow, I., & Bengio, Y. (2016)." in data["apa"]
    assert "Goodfellow" in data["ieee"] and "Bengio" in data["ieee"]
    assert "@article" in data["bibtex"]


def test_api_legacy_humanize(api_client):
    resp = api_client.post(
        "/v1/humanize",
        json={
            "text": "Furthermore, it is important to examine the algorithm.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "humanized_text" in data
    assert data["words_processed"] > 0


def test_api_transform_nul_byte_returns_400(api_client):
    """Prohibited NUL byte in input raises InputError and returns structured 400."""
    resp = api_client.post(
        "/v1/transform",
        json={"text": "Faulty\u0000input text"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"] == "InputError"
    assert data["code"] == "NUL_BYTE_DETECTED"
    assert "NUL" in data["message"]
    assert "detail" in data


def test_api_transform_unknown_ruleset_returns_404(api_client):
    """Unknown ruleset ID raises RulesetError and returns structured 404."""
    resp = api_client.post(
        "/v1/transform",
        json={"text": "Normal text", "ruleset_ids": ["nonexistent_pack_xyz"]},
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "RulesetError"
    assert data["code"] == "RULE_NOT_FOUND"
    assert "nonexistent_pack_xyz" in data["message"]
    assert "detail" in data


def test_api_transform_oversized_payload_returns_422(api_client):
    """Pydantic schema validation caps text length at 500k characters returning 422."""
    resp = api_client.post(
        "/v1/transform",
        json={"text": "A" * 500001},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


def test_api_transform_resource_limit_returns_413(api_client, monkeypatch):
    """Engine ResourceError (e.g. INPUT_TOO_LARGE) returns structured 413 Payload Too Large."""
    from canopus_humanizer.engine.errors import ResourceError, INPUT_TOO_LARGE
    from canopus_humanizer.api import routes

    def mock_process(*args, **kwargs):
        raise ResourceError("Input text exceeds configured memory limit", code=INPUT_TOO_LARGE)

    monkeypatch.setattr(routes._default_pipeline, "process", mock_process)
    resp = api_client.post(
        "/v1/transform",
        json={"text": "Text to trigger resource error"},
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"] == "ResourceError"
    assert data["code"] == "INPUT_TOO_LARGE"
    assert "memory limit" in data["message"]


def test_api_malformed_request_body_returns_422(api_client):
    """Missing required fields or invalid literals return standard 422."""
    resp = api_client.post("/v1/transform", json={})
    assert resp.status_code == 422

    resp_mode = api_client.post("/v1/transform", json={"text": "Hello", "mode": "invalid_mode"})
    assert resp_mode.status_code == 422


def test_api_unexpected_internal_exception_remains_500(monkeypatch):
    """Unexpected non-domain errors (e.g. RuntimeError) remain HTTP 500 and do not expose stack trace."""
    from canopus_humanizer.api import routes

    def mock_process_bug(*args, **kwargs):
        raise RuntimeError("Unexpected server-side hardware or database failure")

    monkeypatch.setattr(routes._default_pipeline, "process", mock_process_bug)
    unhandled_client = TestClient(app, raise_server_exceptions=False)
    resp = unhandled_client.post(
        "/v1/transform",
        json={"text": "Hello world"},
    )
    assert resp.status_code == 500
    assert "Traceback" not in resp.text
    assert "hardware or database failure" not in resp.text
