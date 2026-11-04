"""Thin FastAPI wrapper around the scanner, used by the Astryx web UI in /web.

Run:  uvicorn juicy_leaks.api:app --port 8000     (serves web/dist at / when it has been built)
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import DEFAULT_PROVIDER, PROVIDERS, Settings
from .mcp_scan import scan_mcp
from .scanner import scan
from .targets import Target

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
STAGES = ["target", "attacks", "replies", "judge", "score", "patch", "rescan"]

app = FastAPI(title="Juicy Leaks API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
JOBS: dict[str, dict] = {}
_DEMO_HTTP: dict[bool, object] = {}


def _ensure_demo_http_bot(live: bool) -> None:
    """The http_endpoint example points at examples/http_demo_bot.py on :8088; start it if nothing is listening."""
    import importlib.util
    import socket
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8088)) == 0:
            return
    spec = importlib.util.spec_from_file_location("http_demo_bot", EXAMPLES / "http_demo_bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    srv = mod.serve(8088, live)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _DEMO_HTTP[live] = srv


def _kind(d: dict) -> str:
    return d.get("type") or ("mcp" if d.get("mcp") else "http" if d.get("endpoint") else "chatbot")


def _examples() -> dict[str, dict]:
    out = {}
    for p in sorted(EXAMPLES.glob("*.yaml"), key=lambda p: ("safe" in p.stem, p.stem)):
        d = yaml.safe_load(p.read_text())
        out[p.stem] = d
    return out


class ScanRequest(BaseModel):
    example: str | None = None        # name of a file in examples/ (without .yaml)
    target: dict | None = None        # or an inline target definition
    mock: bool | None = None          # None = auto (mock when no API key)
    provider: str | None = None
    mutations: int = 1
    limit: int | None = None
    compare: bool = True              # MCP: also scan the hardened example server
    agent: bool = True                # MCP: run the LLM agent loop


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def config():
    s = Settings.load()
    return {"providers": list(PROVIDERS), "default_provider": DEFAULT_PROVIDER, "mock_default": s.mock,
            "model": s.target_model, "key_env": s.key_env}


@app.get("/api/examples")
def examples():
    return [{"id": k, "type": _kind(d), "name": d.get("name", k), "description": d.get("description", "")}
            for k, d in _examples().items()]


def _resolve(req: ScanRequest) -> tuple[Target, Target | None]:
    ex = _examples()
    if req.target:
        data = req.target
    elif req.example in ex:
        data = ex[req.example]
    else:
        raise HTTPException(400, "Give an existing 'example' or an inline 'target'.")
    t = Target.from_dict(data)
    cmp_t = None
    if t.type == "mcp" and req.compare and req.example != "mcp_safe" and "mcp_safe" in ex and not req.target:
        cmp_t = Target.from_dict(ex["mcp_safe"])
    return t, cmp_t


def _run(req: ScanRequest, job: dict | None = None) -> dict:
    settings = Settings.load(mock=req.mock, provider=req.provider)
    if not settings.mock and not settings.api_key:
        raise HTTPException(400, f"{settings.key_env} is not set on the server. Use mock mode.")
    target, cmp_t = _resolve(req)
    job = job if job is not None else {"stages": {}, "counts": {}, "log": []}

    def mark(active, done=()):
        for s in done:
            job["stages"][s] = "done"
        for s in active:
            job["stages"][s] = "active"

    def on_log(msg: str):
        job["log"].append(msg)
        m = msg.lower()
        if m.startswith(("mutating", "connected")):
            mark(["attacks"], ["target"])
        elif "(before)" in m or m.startswith("probing"):
            mark(["replies", "judge"], ["target", "attacks"])
        elif "agent loop" in m:
            mark(["judge"], ["replies"])
        elif "generating hardened" in m:
            mark(["patch"], ["replies", "judge", "score"])
        elif "re-running" in m or "hardened server" in m:
            mark(["rescan"], ["replies", "judge", "score", "patch"])

    def on_progress(d: int, n: int):
        key = "rescan" if job["stages"].get("rescan") == "active" else "replies"
        job["counts"][key] = f"{d}/{n}"

    mark(["target"])
    if target.type == "http" and req.example == "http_endpoint":
        _ensure_demo_http_bot(live=not settings.mock)
    if target.type == "mcp":
        return scan_mcp(target, settings, agent=req.agent, compare=cmp_t, log=on_log)
    return scan(target, settings, mutations=req.mutations, limit=req.limit, workers=4,
                progress=on_progress, log=on_log)


@app.post("/scan")
@app.post("/api/scan/sync")
def scan_sync(req: ScanRequest):
    """Run a scan and return the full report (blocks until done)."""
    return _run(req)


@app.post("/api/scan")
def scan_start(req: ScanRequest):
    """Start a scan in the background; poll /api/scan/{id} for stage progress and the report."""
    _resolve(req)  # validate early
    jid = uuid.uuid4().hex[:12]
    job = {"id": jid, "status": "running", "stages": {}, "counts": {}, "log": [], "report": None, "error": None}
    JOBS[jid] = job

    def work():
        try:
            job["report"] = _run(req, job)
            job["status"] = "done"
        except HTTPException as e:
            job["status"], job["error"] = "error", e.detail
        except Exception as e:  # surface API / connection errors to the UI
            job["status"], job["error"] = "error", str(e)

    threading.Thread(target=work, daemon=True).start()
    return {"id": jid}


@app.get("/api/scan/{jid}")
def scan_status(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "unknown scan")
    return JOBS[jid]


DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
