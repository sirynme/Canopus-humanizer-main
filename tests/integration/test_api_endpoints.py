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
