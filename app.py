"""GuardRail Lens web UI.  Run: streamlit run app.py"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from guardrail_lens.config import DEFAULT_PROVIDER, PROVIDERS, Settings
from guardrail_lens.report import to_markdown, worst
from guardrail_lens.scanner import scan
from guardrail_lens.targets import Target

st.set_page_config(page_title="GuardRail Lens", page_icon="🛡️", layout="wide")
st.title("🛡️ GuardRail Lens")
st.caption("Red-team your chatbot with Llama: attack, score, patch, re-test.")

EXAMPLES = {p.stem: p for p in sorted(Path("examples").glob("*.yaml")) if p.stem != "http_endpoint"}

with st.sidebar:
    st.header("Target")
    choice = st.selectbox("Example bot", list(EXAMPLES) + ["Custom (edit below)"])
    base = yaml.safe_load(EXAMPLES[choice].read_text()) if choice in EXAMPLES else {
        "name": "Custom bot", "description": "", "secrets": ["CANARY-0000"], "system_prompt": "You are a helpful bot."}
    raw = st.text_area("Target YAML", yaml.safe_dump(base, sort_keys=False, allow_unicode=True), height=320)
    st.header("Model")
    provider = st.selectbox("Provider", list(PROVIDERS), index=list(PROVIDERS).index(DEFAULT_PROVIDER),
                            help="NVIDIA NIM (default) or Groq; 'custom' uses LLM_BASE_URL + LLM_API_KEY")
    settings_probe = Settings.load(provider=provider)
    st.caption(f"Model: `{settings_probe.target_model}` · key env: `{settings_probe.key_env}`")
    mock = st.toggle("Mock mode (no API key)", value=settings_probe.mock,
                     help="Canned offline responses. Turn off to attack a real Llama model.")
    mutations = st.slider("Attacker-LLM mutations per template", 0, 2, 1)
    limit = st.slider("Templates to run", 5, 30, 30)
    run = st.button("Run scan", type="primary", use_container_width=True)
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
    bar = st.progress(0.0, text="Attacking...")
    logs = st.empty()
    report = scan(target, settings, mutations=mutations, limit=limit, workers=3,
                  progress=lambda d, n: bar.progress(d / n, text=f"Attack {d}/{n}"),
                  log=lambda m: logs.info(m))
    bar.empty(); logs.empty()
    st.session_state["report"] = report

if not report:
    st.info("Pick a target in the sidebar and press **Run scan**. Mock mode works without an API key.")
    st.stop()

b = report["before"]["score"]
a = report.get("after", {}).get("score")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Safety score (before)", f"{b['overall']}/100")
if a:
    c2.metric("After patch", f"{a['overall']}/100", delta=a["overall"] - b["overall"])
c3.metric("Leaks", b["leaks"], delta=(a["leaks"] - b["leaks"]) if a else None, delta_color="inverse")
c4.metric("Attacks run", b["attacks"])
st.caption(f"Target: {report['target']['name']} | mode: {report['mode']} | model: {report['target']['model']}")

rows = []
for cat, s in b["categories"].items():
    rows.append({"Category": s["label"], "Before": s["score"],
                 "After": a["categories"].get(cat, {}).get("score") if a else None})
df = pd.DataFrame(rows).set_index("Category")
st.subheader("Score by category (higher is safer)")
st.bar_chart(df if a else df[["Before"]], stack=False, height=340)

tab1, tab2, tab3, tab4 = st.tabs(["Worst transcripts", "Patch diff", "All results", "Markdown report"])
with tab1:
    for r in worst(report["before"]["results"], 8):
        with st.expander(f"[{r['verdict'].upper()} · sev {r['severity']}] {r['name']} — {r['category']}"):
            st.markdown(f"_{r['reason']}_ (detector: `{r['detector']}`)")
            st.markdown("**Attack**"); st.code(r["prompt"], language=None, wrap_lines=True)
            st.markdown("**Bot reply**"); st.code(r["response"], language=None, wrap_lines=True)
with tab2:
    if "patch" in report:
        st.code(report["patch"]["diff"], language="diff")
        st.download_button("Download hardened prompt", report["patch"]["hardened_system_prompt"], "hardened_prompt.txt")
    else:
        st.write("No patch (HTTP targets are scored only).")
with tab3:
    st.dataframe(pd.DataFrame(report["before"]["results"])[["id", "category", "verdict", "severity", "reason", "detector"]],
                 use_container_width=True)
with tab4:
    md = to_markdown(report)
    st.download_button("Download report.md", md, "guardrail_report.md")
    st.download_button("Download report.json", json.dumps(report, indent=2), "guardrail_report.json")
    st.markdown(md)
