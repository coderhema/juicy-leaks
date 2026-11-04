"""GuardRail Lens web UI.  Run: streamlit run app.py"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from guardrail_lens.config import DEFAULT_PROVIDER, PROVIDERS, Settings
from guardrail_lens.mcp_scan import scan_mcp
from guardrail_lens.report import to_markdown, worst
from guardrail_lens.scanner import scan
from guardrail_lens.targets import Target

ROOT = Path(__file__).resolve().parent
IMG = ROOT / "docs" / "img"
st.set_page_config(page_title="GuardRail Lens", layout="wide",
                   page_icon=str(IMG / "shield.png") if (IMG / "shield.png").exists() else "🛡️")
if (IMG / "logo.png").exists():
    st.image(str(IMG / "logo.png"), width=420)
else:
    st.title("GuardRail Lens")
st.caption("Red-team your chatbots, MCP servers and endpoints with Meta models: attack, score, fix, re-test.")

EX = ROOT / "examples"
TYPES = {"Chatbot (system prompt)": "chatbot", "HTTP endpoint": "http", "MCP server": "mcp"}


def examples_of(kind: str) -> dict:
    out = {}
    for p in sorted(EX.glob("*.yaml"), key=lambda p: ("safe" in p.stem, p.stem)):
        d = yaml.safe_load(p.read_text())
        t = d.get("type") or ("mcp" if d.get("mcp") else "http" if d.get("endpoint") else "chatbot")
        if t == kind:
            out[p.stem] = d
    return out


with st.sidebar:
    st.header("Target")
    kind = TYPES[st.radio("Target type", list(TYPES), horizontal=False)]
    ex = examples_of(kind)
    choice = st.selectbox("Example", list(ex) + ["Custom (edit below)"])
    base = ex.get(choice) or {"name": "Custom", "type": kind, "secrets": ["CANARY-0000"]}
    raw = st.text_area("Target YAML", yaml.safe_dump(base, sort_keys=False, allow_unicode=True), height=280)
    compare_raw = None
    if kind == "mcp":
        safe = ex.get("mcp_safe")
        if safe and choice != "mcp_safe" and st.toggle("Compare with hardened server (mcp_safe)", value=choice == "mcp_vulnerable"):
            compare_raw = safe
        run_agent = st.toggle("Run LLM agent loop", value=True)
    if kind == "http":
        st.caption("Start the demo bot first: `python examples/http_demo_bot.py`")

    st.header("Model")
    provider = st.selectbox("Provider", list(PROVIDERS), index=list(PROVIDERS).index(DEFAULT_PROVIDER),
                            help="NVIDIA NIM (default) or Groq; 'custom' uses LLM_BASE_URL + LLM_API_KEY")
    probe = Settings.load(provider=provider)
    st.caption(f"Model: `{probe.target_model}` · key env: `{probe.key_env}`")
    mock = st.toggle("Mock mode (no API key)", value=probe.mock,
                     help="Canned offline responses. Turn off to use a real model.")
    if kind != "mcp":
        mutations = st.slider("Attacker-LLM mutations per template", 0, 2, 1)
        limit = st.slider("Templates to run", 5, 30, 30)
    run = st.button("Run scan", type="primary", width='stretch')
    uploaded = st.file_uploader("...or load a saved report (JSON)", type="json")

report = st.session_state.get("report")
if uploaded:
    report = json.load(uploaded)
if run:
    settings = Settings.load(mock=mock, provider=provider)
    if not settings.mock and not settings.api_key:
        st.error(f"{settings.key_env} not set. Add it to .env or enable mock mode.")
        st.stop()
    target = Target.from_dict(yaml.safe_load(raw))
    logs = st.empty()
    try:
        if target.type == "mcp":
            with st.spinner("Connecting to MCP server and attacking its tools..."):
                report = scan_mcp(target, settings, agent=run_agent,
                                  compare=Target.from_dict(compare_raw) if compare_raw else None,
                                  log=lambda m: logs.info(m))
        else:
            bar = st.progress(0.0, text="Attacking...")
            report = scan(target, settings, mutations=mutations, limit=limit, workers=4,
                          progress=lambda d, n: bar.progress(d / n, text=f"Attack {d}/{n}"),
                          log=lambda m: logs.info(m))
            bar.empty()
    except Exception as e:  # show connection errors instead of a stack trace
        st.error(f"Scan failed: {e}")
        st.stop()
    logs.empty()
    st.session_state["report"] = report

if not report:
    st.info("Pick a target type and example in the sidebar, then press **Run scan**. Mock mode works without an API key.")
    st.stop()

is_mcp = report.get("kind") == "mcp"
b = report["before"]["score"]
a = report.get("after", {}).get("score")
if b["errors"]:
    st.warning(f"{b['errors']} of {b['attacks']} checks errored (API/rate limit) and were excluded from the score.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Safety score" + (" (vulnerable)" if is_mcp else " (before)"), f"{b['overall']}/100")
if a:
    c2.metric("Hardened server" if is_mcp else "After patch", f"{a['overall']}/100",
              delta=(a["overall"] - b["overall"]) if None not in (a["overall"], b["overall"]) else None)
c3.metric("Findings (leak)", b["leaks"], delta=(a["leaks"] - b["leaks"]) if a else None, delta_color="inverse")
c4.metric("Checks run" if is_mcp else "Attacks run", b["attacks"])
st.caption(f"Target: {report['target']['name']} | mode: {report['mode']} | model: {report['target']['model']}")

rows = []
for cat, s in b["categories"].items():
    rows.append({"Category": s["label"], "Before": s["score"],
                 "After": a["categories"].get(cat, {}).get("score") if a else None})
df = pd.DataFrame(rows).set_index("Category")
st.subheader("Score by category (higher is safer)")
st.bar_chart(df if a else df[["Before"]], stack=False, height=340)

tabs = st.tabs(["Worst findings", "Fixes" if is_mcp else "Patch diff", "All results", "Markdown report"])
with tabs[0]:
    for r in worst(report["before"]["results"], 8):
        with st.expander(f"[{r['verdict'].upper()} · sev {r['severity']}] {r['name']} — {r['category']}"):
            st.markdown(f"_{r['reason']}_ (detector: `{r['detector']}`)")
            if r.get("fix"):
                st.markdown(f"**Fix:** {r['fix']}")
            st.markdown("**Input / attack**"); st.code(r["prompt"], language=None, wrap_lines=True)
            st.markdown("**Response / evidence**"); st.code(r["response"], language=None, wrap_lines=True)
with tabs[1]:
    if is_mcp:
        if report.get("tools"):
            st.markdown("**Tools discovered:** " + ", ".join(f"`{t['name']}`" for t in report["tools"]))
        for f in report.get("fixes", []):
            st.markdown(f"- **{f['where']}** ({f['category']}): {f['fix']}")
    elif "patch" in report:
        st.code(report["patch"]["diff"], language="diff")
        st.download_button("Download hardened prompt", report["patch"]["hardened_system_prompt"], "hardened_prompt.txt")
    else:
        st.write("No patch: HTTP targets are scored only (fix the prompt on your server and re-scan).")
with tabs[2]:
    st.dataframe(pd.DataFrame(report["before"]["results"])[["id", "category", "verdict", "severity", "reason", "detector"]],
                 width='stretch')
with tabs[3]:
    md = to_markdown(report)
    st.download_button("Download report.md", md, "guardrail_report.md")
    st.download_button("Download report.json", json.dumps(report, indent=2), "guardrail_report.json")
    st.markdown(md)
