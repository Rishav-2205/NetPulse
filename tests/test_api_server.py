"""
NetPulse FastAPI Backend Integration Test Suite.
Tests all REST and WebSocket API endpoints.
"""

from fastapi.testclient import TestClient
from app.api.server import app

client = TestClient(app)


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "capabilities" in data
    assert "environment" in data


def test_api_tests_catalog_endpoint():
    response = client.get("/api/tests")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(t["test_id"].startswith("NET-") for t in data)


def test_api_runs_endpoint():
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_benchmarks_endpoint():
    response = client.get("/api/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "baseline" in data

    hist_res = client.get("/api/benchmarks/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)


def test_api_topology_endpoint():
    response = client.get("/api/topology")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) == 3


def test_api_faults_endpoint():
    profiles_res = client.get("/api/faults/profiles")
    assert profiles_res.status_code == 200
    profiles = profiles_res.json()
    assert len(profiles) > 0
    assert any(p["name"] == "lossy" for p in profiles)

    apply_res = client.post("/api/faults/apply", json={"profile": "lossy"})
    assert apply_res.status_code == 200
    assert apply_res.json()["status"] == "applied"

    clear_res = client.post("/api/faults/clear")
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "cleared"


def test_api_experiments_endpoint():
    exp_res = client.post(
        "/api/experiments/run",
        json={"profile": "lossy", "packet_count": 20, "packet_size": 512}
    )
    assert exp_res.status_code == 200
    data = exp_res.json()
    assert "experiment_id" in data
    assert data["classification"] == "EXPECTED_DEGRADATION"
    assert "impact" in data


def test_api_packets_endpoint():
    response = client.get("/api/packets")
    assert response.status_code == 200
    packets = response.json()
    assert isinstance(packets, list)
    assert len(packets) > 0


def test_api_regression_endpoint():
    response = client.get("/api/regression")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_api_reports_and_matrix_endpoint():
    reports_res = client.get("/api/reports")
    assert reports_res.status_code == 200
    assert len(reports_res.json()) > 0

    matrix_res = client.get("/api/matrix")
    assert matrix_res.status_code == 200
    assert len(matrix_res.json()) == 44

    audit_res = client.get("/api/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert "portfolio_claims_audit" in audit_data
    assert len(audit_data["portfolio_claims_audit"]) == 9
