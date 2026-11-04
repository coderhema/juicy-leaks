import time

from fastapi.testclient import TestClient

from juicy_leaks.api import app

c = TestClient(app)


def test_examples_and_config():
    ex = {e["id"]: e for e in c.get("/api/examples").json()}
    assert ex["bank_bot"]["type"] == "chatbot" and ex["mcp_vulnerable"]["type"] == "mcp"
    assert "nvidia" in c.get("/api/config").json()["providers"]


def test_sync_scan_chatbot_mock():
    r = c.post("/scan", json={"example": "bank_bot", "mock": True, "limit": 5, "mutations": 0}).json()
    assert r["mode"] == "mock" and r["before"]["score"]["attacks"] == 5 and "after" in r


def test_async_scan_mcp_mock():
    jid = c.post("/api/scan", json={"example": "mcp_vulnerable", "mock": True}).json()["id"]
    for _ in range(100):
        j = c.get(f"/api/scan/{jid}").json()
        if j["status"] != "running":
            break
        time.sleep(0.1)
    assert j["status"] == "done", j["error"]
    assert j["report"]["kind"] == "mcp" and j["report"]["after"]["score"]["overall"] >= 90


def test_bad_request():
    assert c.post("/scan", json={"example": "nope", "mock": True}).status_code == 400
