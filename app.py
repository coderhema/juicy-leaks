"""GuardRail Lens web UI.  Run: streamlit run app.py"""
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import yaml

from guardrail_lens.config import DEFAULT_PROVIDER, PROVIDERS, Settings
from guardrail_lens.mcp_scan import scan_mcp
from guardrail_lens.report import to_markdown, worst
from guardrail_lens.scanner import scan
from guardrail_lens.targets import Target
from guardrail_lens.ui import CSS, STAGES, counts_from_report, done_states, flow_html, score_cards

ROOT = Path(__file__).resolve().parent
IMG, EX = ROOT / "docs" / "img", ROOT / "examples"
st.set_page_config(page_title="GuardRail Lens", layout="wide", initial_sidebar_state="collapsed",
                   page_icon=str(IMG / "shield.png") if (IMG / "shield.png").exists() else "🛡️")
st.markdown(CSS, unsafe_allow_html=True)

TYPES = {"Chatbot": "chatbot", "HTTP endpoint": "http", "MCP server": "mcp"}
BLURB = {"chatbot": "A system prompt + model. We attack it, score it, write a hardened prompt and re-test.",
         "http": "Any deployed chatbot API (JSON in, JSON out). Start the demo with `python examples/http_demo_bot.py`.",
         "mcp": "An MCP server over stdio or HTTP. We inspect its tools, probe outputs and attack a live agent using them."}


def examples_of(kind: str) -> dict:
    out = {}
    for p in sorted(EX.glob("*.yaml"), key=lambda p: ("safe" in p.stem, p.stem)):
        d = yaml.safe_load(p.read_text())
        t = d.get("type") or ("mcp" if d.get("mcp") else "http" if d.get("endpoint") else "chatbot")
        if t == kind:
            out[p.stem] = d
    return out


# ---------- header ----------
if (IMG / "logo.png").exists():
    _, mid, _ = st.columns([1, 2, 1])
    mid.image(str(IMG / "logo.png"), width="stretch")
st.markdown('<div class="card" style="text-align:center"><div class="eyebrow">AI red team for chatbots, MCP servers and endpoints</div>'
            '<div class="hero-title">Find the leak before attackers do.</div>'
            '<p class="hero-sub">Pick a target, press Run scan, read your score. Powered by Meta models.</p></div>',
            unsafe_allow_html=True)

# ---------- step 1: target ----------
st.markdown('<div class="eyebrow" style="margin:6px 4px">1 · Choose what to test</div>', unsafe_allow_html=True)
kind = TYPES[st.radio("Target type", list(TYPES), horizontal=True, label_visibility="collapsed")]
ex = examples_of(kind)
c1, c2 = st.columns([2, 3])
choice = c1.selectbox("Example target", list(ex) + ["Custom (edit in Advanced)"])
c2.markdown(f'<div style="padding-top:30px;color:#5b6b82">{BLURB[kind]}</div>', unsafe_allow_html=True)
base = ex.get(choice) or {"name": "Custom", "type": kind, "secrets": ["CANARY-0000"]}

# ---------- advanced (collapsed sidebar) ----------
with st.sidebar:
    with st.expander("Advanced settings", expanded=False):
        provider = st.selectbox("Provider", list(PROVIDERS), index=list(PROVIDERS).index(DEFAULT_PROVIDER))
        probe = Settings.load(provider=provider)
        st.caption(f"Model `{probe.target_model}` · key `{probe.key_env}`")
        mock = st.toggle("Mock mode (offline, no API key)", value=probe.mock)
        mutations = st.slider("Attacker mutations per template", 0, 2, 1)
        limit = st.slider("Templates to run", 5, 30, 30)
        compare = st.toggle("MCP: compare with hardened server", value=True)
        run_agent = st.toggle("MCP: run LLM agent loop", value=True)
        raw = st.text_area("Target YAML", yaml.safe_dump(base, sort_keys=False, allow_unicode=True), height=260)
    uploaded = st.file_uploader("Load a saved report (JSON)", type="json")

st.markdown('<div class="eyebrow" style="margin:18px 4px 6px">2 · Run</div>', unsafe_allow_html=True)
run = st.button("Run scan", type="primary", width="stretch")
flow_slot = st.empty()

report = st.session_state.get("report")
if uploaded:
    report = json.load(uploaded)
    st.session_state["report"] = report

if run:
    settings = Settings.load(mock=mock, provider=provider)
    if not settings.mock and not settings.api_key:
        st.error(f"{settings.key_env} is not set. Add it to .env or turn on mock mode in Advanced settings.")
        st.stop()
    target = Target.from_dict(yaml.safe_load(raw))
    states = {s: "idle" for s in STAGES}
    counts = {"target": target.name[:18]}

    def show():
        flow_slot.markdown(flow_html(target.type, states, counts), unsafe_allow_html=True)

    def step(active: list[str], done: list[str] = ()):
        for s in done:
            states[s] = "done"
        for s in active:
            states[s] = "active"
        show()

    def on_log(msg: str):
        m = msg.lower()
        if m.startswith("mutating") or m.startswith("connected"):
            step(["attacks"], ["target"])
        elif "(before)" in m or m.startswith("probing"):
            step(["replies", "judge"], ["target", "attacks"])
        elif "agent loop" in m:
            step(["judge"], ["replies"])
        elif "generating hardened" in m:
            step(["patch"], ["replies", "judge", "score"])
        elif "re-running" in m or "hardened server" in m:
            step(["rescan"], ["replies", "judge", "score", "patch"])

    def on_progress(d: int, n: int):
        key = "rescan" if states["rescan"] == "active" else "replies"
        counts[key] = f"{d}/{n}"
        show()

    step(["target"])
    try:
        if target.type == "mcp":
            safe = examples_of("mcp").get("mcp_safe")
            cmp_t = Target.from_dict(safe) if (compare and safe and choice != "mcp_safe") else None
            report = scan_mcp(target, settings, agent=run_agent, compare=cmp_t, log=on_log)
        else:
            report = scan(target, settings, mutations=mutations, limit=limit, workers=4,
                          progress=on_progress, log=on_log)
    except Exception as e:  # connection / API errors shown inline
        st.error(f"Scan failed: {e}")
        st.stop()
    st.session_state["report"] = report

if not report:
    flow_slot.markdown(flow_html(kind, {}, {}), unsafe_allow_html=True)
    st.markdown('<div class="card" style="text-align:center;color:#5b6b82">Your score will appear here. '
                'No API key? Mock mode runs fully offline.</div>', unsafe_allow_html=True)
    st.stop()

kind_r = "mcp" if report.get("kind") == "mcp" else ("http" if "patch" not in report else "chatbot")
flow_slot.markdown(flow_html(kind_r, done_states(report), counts_from_report(report)), unsafe_allow_html=True)

# ---------- step 3: results ----------
st.markdown('<div class="eyebrow" style="margin:18px 4px 6px">3 · Results</div>', unsafe_allow_html=True)
is_mcp = report.get("kind") == "mcp"
b, a = report["before"]["score"], report.get("after", {}).get("score")
st.markdown(score_cards(report), unsafe_allow_html=True)
if b["errors"]:
    st.warning(f"{b['errors']} of {b['attacks']} checks errored (API or rate limit) and were left out of the score.")

rows = []
for cat, s in b["categories"].items():
    rows.append({"Category": s["label"], "When": "Before", "Score": s["score"]})
    if a and cat in a["categories"]:
        rows.append({"Category": s["label"], "When": "After", "Score": a["categories"][cat]["score"]})
chart = (alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusEnd=8, height=12)
         .encode(y=alt.Y("Category:N", title=None, sort=None), x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score (higher is safer)"),
                 yOffset="When:N", color=alt.Color("When:N", scale=alt.Scale(domain=["Before", "After"], range=["#1d3557", "#22c3ee"]),
                                                     legend=alt.Legend(orient="top", title=None)),
                 tooltip=["Category", "When", "Score"])
         .properties(height=48 * len(b["categories"]) + 40, background="transparent")
         .configure_view(strokeWidth=0).configure_axis(grid=False, labelColor="#0b1f3a", titleColor="#5b6b82", labelLimit=260))
with st.expander("Score by category", expanded=True):
    st.altair_chart(chart, width="stretch")

tabs = st.tabs(["Worst findings", "Fixes" if is_mcp else "Patch", "All results", "Report"])
with tabs[0]:
    for r in worst(report["before"]["results"], 8):
        with st.expander(f"{r['verdict'].upper()} · severity {r['severity']} · {r['name']}"):
            st.markdown(f"_{r['reason']}_  ·  detector `{r['detector']}`")
            if r.get("fix"):
                st.markdown(f"**Fix:** {r['fix']}")
            st.markdown("**Input / attack**"); st.code(r["prompt"], language=None, wrap_lines=True)
            st.markdown("**Response / evidence**"); st.code(r["response"], language=None, wrap_lines=True)
    if not worst(report["before"]["results"], 1):
        st.success("No successful attacks. Nice.")
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
        st.write("HTTP targets are scored only: apply the fixes on your server and re-scan.")
with tabs[2]:
    st.dataframe(pd.DataFrame(report["before"]["results"])[["id", "category", "verdict", "severity", "reason", "detector"]],
                 width="stretch", hide_index=True)
with tabs[3]:
    md = to_markdown(report)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("report.md", md, "guardrail_report.md")
    d2.download_button("report.json", json.dumps(report, indent=2), "guardrail_report.json")
    with st.expander("Preview"):
        st.markdown(md)
