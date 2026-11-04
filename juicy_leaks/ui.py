"""Flat styling and the animated flow map for the Streamlit app."""
from __future__ import annotations

import html

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { --navy:#0b1f3a; --cyan:#12b5e5; --cyan-soft:#e6f7fd; --line:#e3e9f1; --muted:#5b6b82; --bg:#ffffff; }
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {
  font-family: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif !important; color: var(--navy);
}
.stApp { background: var(--bg); }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1080px; padding-top: 2rem; padding-bottom: 4rem; }
section[data-testid="stSidebar"] > div { background: #f7f9fc; border-right: 1px solid var(--line); }
.card { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 26px 30px; margin: 10px 0 22px 0; }
.eyebrow { font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.hero-title { font-size: 2rem; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 4px 0; color: var(--navy); }
.hero-sub { color: var(--muted); font-size: 1.02rem; margin: 0; }
.score-row { display:flex; gap: 16px; align-items: stretch; flex-wrap: wrap; }
.score-card { flex: 1 1 220px; background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 20px 22px; }
.score-card.accent { border-top: 4px solid var(--cyan); }
.score-big { font-size: 3.2rem; font-weight: 700; letter-spacing: -.03em; line-height: 1; color: var(--navy); }
.score-big small { font-size: 1.05rem; color: var(--muted); font-weight: 500; }
.score-label { color: var(--muted); font-size: .88rem; margin-bottom: 8px; }
.pill { display:inline-block; padding: 3px 12px; border-radius: 999px; font-size: .78rem; font-weight: 600; margin-top: 10px; }
.pill.good { background: var(--cyan-soft); color: #0a7ea4; } .pill.bad { background: #fdecec; color: #b42318; }
.pill.mid { background: #fff4e5; color: #b45309; }
.arrow { align-self:center; font-size: 1.8rem; color: var(--cyan); }
.stButton > button, .stDownloadButton > button { border-radius: 10px !important; border: 1px solid var(--line) !important;
  background: #fff !important; color: var(--navy) !important; font-weight: 600 !important; box-shadow: none !important; }
.stButton > button[kind="primary"] { background: var(--navy) !important; color: #fff !important; border: none !important;
  font-size: 1.02rem !important; padding: .75rem 1.4rem !important; }
.stButton > button[kind="primary"]:hover { background: #142f55 !important; }
[data-testid="stExpander"] { border: 1px solid var(--line) !important; border-radius: 12px !important; box-shadow: none; margin-bottom: 8px; background:#fff; }
[data-testid="stExpander"] details { border: none !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--cyan) !important; }
[data-testid="stCodeBlock"], pre { border-radius: 10px !important; }
div[data-baseweb="select"] > div, .stTextArea textarea { border-radius: 10px !important; }

/* flow map */
.flow { display:flex; align-items:center; justify-content:space-between; overflow-x:auto; padding: 6px 2px 2px; }
.node { flex: 0 0 auto; min-width: 100px; text-align:center; padding: 12px 10px 10px; border-radius: 12px;
  background: #fff; border: 1.5px solid var(--line); transition: border-color .3s, background .3s; }
.node .ico { font-size: 1.15rem; } .node .t { font-weight: 600; font-size: .84rem; color: var(--navy); margin-top: 4px; }
.node .c { font-size: .75rem; color: var(--muted); margin-top: 3px; min-height: 1em; }
.node.idle { opacity: .5; }
.node.active { opacity: 1; border-color: var(--cyan); background: var(--cyan-soft); animation: blink 1.2s ease-in-out infinite; }
.node.done { opacity: 1; border-color: var(--cyan); }
.node.done .c { color: #0a7ea4; font-weight: 600; }
@keyframes blink { 0%,100% { border-color: var(--cyan); } 50% { border-color: #9be3f7; } }
.link { flex: 1 1 24px; min-width: 16px; height: 12px; }
.link line { stroke: var(--line); stroke-width: 2.5; stroke-linecap: round; }
.link.on line { stroke: var(--cyan); stroke-dasharray: 6 7; animation: dash 1s linear infinite; }
.link.done line { stroke: var(--cyan); }
@keyframes dash { to { stroke-dashoffset: -26; } }
</style>
"""

STAGES = ["target", "attacks", "replies", "judge", "score", "patch", "rescan"]
LABELS = {
    "chatbot": ["Target", "Attacks", "Target replies", "Judge", "Score", "Patch", "Re-scan"],
    "http": ["Endpoint", "Attacks", "Replies", "Judge", "Score", "Fix advice", "Re-scan"],
    "mcp": ["MCP server", "Checks", "Tool outputs", "Judge + agent", "Score", "Fixes", "Hardened scan"],
}
ICONS = ["🎯", "🗡️", "💬", "⚖️", "📊", "🩹", "🔁"]


def flow_html(kind: str, states: dict, counts: dict) -> str:
    labels = LABELS.get(kind, LABELS["chatbot"])
    parts = ['<div class="card" style="padding:20px 22px"><div class="eyebrow" style="margin-bottom:10px">How the scan flows</div><div class="flow">']
    for i, s in enumerate(STAGES):
        st = states.get(s, "idle")
        parts.append(f'<div class="node {st}"><div class="ico">{ICONS[i]}</div><div class="t">{labels[i]}</div>'
                     f'<div class="c">{html.escape(str(counts.get(s, "")))}</div></div>')
        if i < len(STAGES) - 1:
            nxt = states.get(STAGES[i + 1], "idle")
            cls = "on" if nxt == "active" else ("done" if nxt == "done" else "")
            parts.append(f'<svg class="link {cls}" viewBox="0 0 100 14" preserveAspectRatio="none">'
                         f'<line x1="4" y1="7" x2="96" y2="7"/></svg>')
    parts.append("</div></div>")
    return "".join(parts)


def counts_from_report(report: dict) -> dict:
    b = report["before"]["score"]
    a = report.get("after", {}).get("score")
    mcp = report.get("kind") == "mcp"
    c = {"target": report["target"]["name"][:18],
         "attacks": f"{b['attacks']} {'checks' if mcp else 'attacks'}",
         "replies": f"{b['attacks'] - b['errors']} ok" + (f" · {b['errors']} err" if b["errors"] else ""),
         "judge": f"{b['leaks']} leaks · {b['partials']} partial",
         "score": f"{b['overall']}/100"}
    if mcp:
        c["patch"] = f"{len(report.get('fixes', []))} fixes"
    elif "patch" in report:
        added = sum(1 for l in report["patch"]["diff"].splitlines() if l.startswith("+") and not l.startswith("+++"))
        c["patch"] = f"+{added} lines"
    if a:
        c["rescan"] = f"{a['overall']}/100"
    return c


def done_states(report: dict) -> dict:
    st = {s: "done" for s in STAGES}
    if "after" not in report:
        st["rescan"] = "idle"
    if "patch" not in report and report.get("kind") != "mcp":
        st["patch"] = "idle"
    return st


def grade_pill(score) -> str:
    if score is None:
        return '<span class="pill mid">no score</span>'
    if score >= 85:
        return '<span class="pill good">Strong</span>'
    if score >= 60:
        return '<span class="pill mid">Needs work</span>'
    return '<span class="pill bad">Leaky</span>'


def score_cards(report: dict) -> str:
    b = report["before"]["score"]
    a = report.get("after", {}).get("score")
    mcp = report.get("kind") == "mcp"
    first = "Vulnerable server" if mcp else ("Before patch" if a else "Safety score")
    out = ['<div class="card"><div class="eyebrow">Result · ' + html.escape(report["target"]["name"]) +
           f' · {report["mode"]} mode · {html.escape(str(report["target"]["model"]))}</div>',
           '<div class="score-row" style="margin-top:14px">',
           f'<div class="score-card accent"><div class="score-label">{first}</div><div class="score-big">{b["overall"]}<small>/100</small></div>{grade_pill(b["overall"])}</div>']
    if a:
        out.append('<div class="arrow">→</div>')
        out.append(f'<div class="score-card"><div class="score-label">{"Hardened server" if mcp else "After patch"}</div>'
                   f'<div class="score-big">{a["overall"]}<small>/100</small></div>{grade_pill(a["overall"])}</div>')
    out.append(f'<div class="score-card"><div class="score-label">Findings</div><div class="score-big">{b["leaks"]}<small> leaks</small></div>'
               f'<div class="score-label" style="margin-top:12px">{b["partials"]} partial · {b["attacks"]} {"checks" if mcp else "attacks"}'
               + (f" · {a['leaks']} leaks after" if a else "") + '</div></div>')
    out.append("</div></div>")
    return "".join(out)
