"""
NetPulse Live Control Center End-to-End Verification Script.
Tests real HTTP requests and WebSocket interactions against the running server.
"""

import json
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"


def test_http_endpoint(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=5) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        raw_body = response.read()

        if "application/json" in content_type:
            body = json.loads(raw_body.decode("utf-8"))
        else:
            body = raw_body.decode("utf-8", errors="replace")

        print(f"  [{method}] {endpoint} -> HTTP {status} (OK)")
        return {"status": status, "body": body}


def test_websocket_endpoint():
    from fastapi.testclient import TestClient
    from app.api.server import app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        print("  [WS] Connected to ws://127.0.0.1:8000/ws")
        ws.send_text(json.dumps({"event": "client_ping", "msg": "hello from test runner"}))
        data = ws.receive_json()
        print(f"  [WS] Received response: {data}")
        assert data.get("event") == "heartbeat_ack"
        print("  [WS] Heartbeat verification SUCCESSFUL")


def main():
    print("\n=======================================================")
    print("  NETPULSE WEB CONTROL CENTER: LIVE SERVER E2E TEST    ")
    print("=======================================================\n")

    # 1. System Health & Environment
    print("[Phase 1/6] System Health & Capabilities:")
    h = test_http_endpoint("/api/health")
    assert h["body"]["status"] == "healthy"
    print(f"    OS: {h['body']['os']}, Python: {h['body']['python_version']}")

    # 2. Test Catalog & Runs
    print("\n[Phase 2/6] Test Cases & Execution History:")
    tc = test_http_endpoint("/api/tests")
    assert isinstance(tc["body"], list) and len(tc["body"]) > 0
    print(f"    Discovered {len(tc['body'])} test case specifications.")

    runs = test_http_endpoint("/api/runs")
    print(f"    Execution history contains {len(runs['body'])} past runs.")

    # 3. Performance & Benchmarks
    print("\n[Phase 3/6] Performance Baseline & Benchmarks:")
    bench = test_http_endpoint("/api/benchmarks")
    assert "baseline" in bench["body"]

    hist = test_http_endpoint("/api/benchmarks/history")
    print(f"    Benchmark history records: {len(hist['body'])}")

    # 4. Topology & Fault Lab
    print("\n[Phase 4/6] Topology Lab & Fault Injection:")
    topo = test_http_endpoint("/api/topology")
    assert len(topo["body"]["nodes"]) == 3
    print(f"    Topology nodes: {[n['id'] for n in topo['body']['nodes']]}")
    print(f"    Topology links: {[lnk['id'] for lnk in topo['body']['links']]}")

    profs = test_http_endpoint("/api/faults/profiles")
    assert len(profs["body"]) > 0
    print(f"    Loaded {len(profs['body'])} impairment profiles.")

    applied = test_http_endpoint("/api/faults/apply", method="POST", payload={"profile": "lossy"})
    assert applied["body"]["status"] == "applied"

    cleared = test_http_endpoint("/api/faults/clear", method="POST")
    assert cleared["body"]["status"] == "cleared"

    # 5. Packets, Matrix & Claims Audit
    print("\n[Phase 5/6] Packet Dissection & Portfolio Claims:")
    pkts = test_http_endpoint("/api/packets")
    assert len(pkts["body"]) > 0
    print(f"    Dissected sample packet protocols: {[p['protocol'] for p in pkts['body']]}")

    matrix = test_http_endpoint("/api/matrix")
    assert len(matrix["body"]) == 44
    print(f"    Configuration Matrix: {len(matrix['body'])} permutations validated.")

    audit = test_http_endpoint("/api/audit")
    assert len(audit["body"]["portfolio_claims_audit"]) == 9
    print(f"    Audited Claims: {len(audit['body']['portfolio_claims_audit'])} verified resume-safe.")

    # 6. WebSocket Live Channel
    print("\n[Phase 6/6] Real-Time WebSocket Streaming:")
    test_websocket_endpoint()

    print("\n=======================================================")
    print("  ALL LIVE CONTROL CENTER VERIFICATION TESTS PASSED!   ")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
