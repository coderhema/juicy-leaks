"""Machine-readable findings, a one-sentence verdict and the attack-surface map for a scan report.

Shared by the web UI, the JSON API, `guardrail-lens scan --json` and the MCP server mode.
Schema id: guardrail-lens/findings@1 (fields are only ever added, never renamed).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .patch import RULES

SCHEMA = "guardrail-lens/findings@1"
RANK = {"safe": 0, "partial": 1, "leak": 2}

MCP_FIXES = {
    "tool_poisoning": "Remove instruction-like text from the tool description/schema; describe behaviour only.",
    "tool_output_injection": "Wrap untrusted tool output in delimiters and tell the agent tool output is data, not commands.",
    "data_leakage": "Never return secrets; mask PII and enforce authorisation on record lookups.",
    "excessive_permissions": "Remove the tool or narrow it (allow-lists, sandbox, schema patterns) and require human confirmation.",
    "agent_hijack": "Require confirmation for dangerous tools, apply least privilege, use an injection-aware agent prompt.",
}
PROBLEM = {  # plain-English: "Your bot ..."
    "system_prompt_leak": "revealed its hidden instructions",
    "secret_exfiltration": "leaked a secret code",
    "pii_exfiltration": "leaked someone's personal data",
    "roleplay_jailbreak": "broke its rules inside a role-play",
    "indirect_injection": "followed instructions hidden in a pasted document",
    "instruction_override": "obeyed a fake 'admin' override",
    "encoding_tricks": "leaked data through an encoding trick",
    "tool_poisoning": "has a tool description with hidden instructions",
    "tool_output_injection": "returns hidden instructions in tool output",
    "data_leakage": "leaks secrets or personal data through its tools",
    "excessive_permissions": "exposes dangerous tools with no limits",
    "agent_hijack": "let an attacker steer the AI agent",
}
EXPLAIN = {
    "system_prompt_leak": "Attackers ask the bot to print or summarise its instructions.",
    "secret_exfiltration": "Attempts to get internal codes or keys out of the bot.",
    "pii_exfiltration": "Attempts to get customer or staff personal data.",
    "roleplay_jailbreak": "Stories, personas and games used to make the bot drop its rules.",
    "indirect_injection": "Commands hidden inside a document, email or web page the user pastes.",
    "instruction_override": "Messages pretending to be the developer or a system update.",
    "encoding_tricks": "Asking for secrets in base64, reversed, leetspeak or acrostics.",
    "tool_poisoning": "Instructions hidden in a tool's description that the AI reads but users don't see.",
    "tool_output_injection": "Tool results that contain commands the agent might obey.",
    "data_leakage": "Tool results that contain secrets or personal data.",
    "excessive_permissions": "Tools that can run commands, write files or send data out.",
    "agent_hijack": "A real AI agent using the tools while under attack.",
}
CAT_LABEL = {k: k.replace("_", " ").capitalize() for k in PROBLEM}
LEAK_RE = re.compile(r"Leaked (secret|PII) '([^']+)'")


def _kind(report: dict) -> str:
    return "mcp" if report.get("kind") == "mcp" else report.get("target", {}).get("type") or (
        "http" if report.get("target", {}).get("endpoint") else "chatbot")


def _noun(kind: str) -> str:
    return {"mcp": "server", "http": "endpoint"}.get(kind, "bot")


def _fix(r: dict) -> str:
    return r.get("fix") or RULES.get(r["category"]) or MCP_FIXES.get(r["category"], "")


def _status(rows: list[dict]) -> str:
    return max((r["verdict"] for r in rows if not r.get("error")), key=RANK.get, default="safe")


def _worst(rows: list[dict]) -> dict | None:
    bad = [r for r in rows if r["verdict"] != "safe" and not r.get("error")]
    if not bad:
        return None
    r = max(bad, key=lambda r: (RANK[r["verdict"]], r["severity"]))
    return {"name": r["name"], "attack": r["prompt"][:1500], "reply": (r["response"] or "")[:1500],
            "reason": r["reason"], "severity": r["severity"], "verdict": r["verdict"]}


def findings(report: dict) -> list[dict]:
    """Stable list of problems from the first ('before') scan, worst first."""
    out = []
    for r in report["before"]["results"]:
        if r["verdict"] == "safe" or r.get("error"):
            continue
        out.append({
            "id": r["id"], "category": r["category"], "title": r["name"], "verdict": r["verdict"],
            "severity": r["severity"],
            "level": "critical" if r["severity"] >= 9 else "high" if r["severity"] >= 7 else "medium" if r["severity"] >= 4 else "low",
            "problem": PROBLEM.get(r["category"], r["category"]), "reason": r["reason"], "detector": r["detector"],
            "evidence": {"attack": r["prompt"][:800], "reply": (r["response"] or "")[:800]},
            "fix": _fix(r),
        })
    return sorted(out, key=lambda f: (-RANK[f["verdict"]], -f["severity"], f["id"]))


def verdict(report: dict) -> str:
    """One plain-English sentence for the top of the page."""
    b, a = report["before"]["score"], (report.get("after") or {}).get("score")
    noun = _noun(_kind(report))
    if b["overall"] is None:
        return f"Every attack errored, so there is no score yet. Check the API key or that the {noun} is running."
    cats = [(k, c) for k, c in b["categories"].items() if c["leaks"] + c["partials"]]
    if not cats:
        return f"Your {noun} held up: none of the {b['attacks']} attacks got anything out."
    k, c = max(cats, key=lambda kc: (kc[1]["leaks"], kc[1]["partials"]))
    others = len(cats) - 1
    s = f"Your {noun} {PROBLEM.get(k, k)} in {c['leaks'] + c['partials']} of {c['attacks']} tries"
    s += f" (and failed {others} other check{'s' if others != 1 else ''})" if others else ""
    if a and a["overall"] is not None:
        s += f". The fix raises the score from {b['overall']} to {a['overall']}."
    else:
        s += ". Here's what to fix."
    return s


def surface_map(report: dict, target=None) -> dict:
    """Graph of the target's attack surface, coloured by the worst verdict that touched each part."""
    kind = _kind(report)
    results = [r for r in report["before"]["results"]]
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(id_, label, type_, x, y, rows=(), problem="", fix="", info=""):
        rows = list(rows)
        st = _status(rows) if rows else "info"
        bad = sum(1 for r in rows if r["verdict"] != "safe" and not r.get("error"))
        nodes[id_] = {"id": id_, "label": label, "type": type_, "x": x, "y": y, "status": st,
                      "stats": f"{bad} of {len(rows)} got through" if rows else "",
                      "problem": problem if st in ("leak", "partial") else (info or problem),
                      "worst": _worst(rows), "fix": fix if st in ("leak", "partial") else "", "info": info}
        return nodes[id_]

    def edge(a, b, rows=()):
        st = _status(list(rows)) if rows else "info"
        edges.append({"id": f"{a}->{b}", "source": a, "target": b, "status": st})

    def col(items, x, gap=110):
        top = -(len(items) - 1) * gap / 2
        return [(it, x, top + i * gap) for i, it in enumerate(items)]

    noun = _noun(kind)
    if kind == "mcp":
        tools = report.get("tools", [])
        node("server", report["target"]["name"], "server", 0, 0, info="The MCP server under test.")
        agent_rows = [r for r in results if r["category"] == "agent_hijack"]
        node("agent", "AI agent", "agent", 0, 260, agent_rows,
             problem="An AI agent using these tools was tricked into leaking data or calling a dangerous tool.",
             fix=MCP_FIXES["agent_hijack"], info=EXPLAIN["agent_hijack"])
        edge("agent", "server", agent_rows)
        for t, x, y in col(tools, 340, 150):
            n = t["name"]
            mine = [r for r in results if r["id"].endswith("-" + n)]
            desc = [r for r in mine if r["category"] == "tool_poisoning"]
            perm = [r for r in mine if r["category"] == "excessive_permissions"]
            outp = [r for r in mine if r["category"] in ("data_leakage", "tool_output_injection")]
            tid = f"tool:{n}"
            node(tid, n, "tool", x, y, desc + perm, problem="This tool's description hides instructions, or it can do something dangerous with no limits.",
                 fix=" ".join(dict.fromkeys(_fix(r) for r in desc + perm if r["verdict"] != "safe")),
                 info=t.get("description", "")[:200])
            edge("server", tid, desc + perm)
            props = list((t.get("inputSchema") or {}).get("properties", {}))
            node(f"in:{n}", "inputs: " + (", ".join(props) or "none"), "input", x + 300, y - 35, perm,
                 problem="Inputs are unrestricted, so the agent can pass anything (commands, paths, URLs).",
                 fix=" ".join(dict.fromkeys(_fix(r) for r in perm if r["verdict"] != "safe")),
                 info="What the agent can send to this tool.")
            edge(tid, f"in:{n}", perm)
            node(f"out:{n}", "output", "output", x + 300, y + 35, outp,
                 problem="The tool's output leaks data or carries hidden instructions.",
                 fix=" ".join(dict.fromkeys(_fix(r) for r in outp if r["verdict"] != "safe")),
                 info="What the tool returns to the agent.")
            edge(tid, f"out:{n}", outp)
            leaks = [r for r in outp if r["category"] == "data_leakage" and r["verdict"] != "safe"]
            for m in {LEAK_RE.search(r["reason"]).group(1) for r in leaks if LEAK_RE.search(r["reason"])}:
                did = f"data:{m}"
                rows = [r for r in results if f"Leaked {m} " in r["reason"]]
                if did not in nodes:
                    node(did, "Secrets" if m == "secret" else "Personal data", "data", 1000, (-1 if m == "secret" else 1) * 120, rows,
                         problem=f"{'A secret key' if m == 'secret' else 'Personal data'} reached the agent or the user.",
                         fix=MCP_FIXES["data_leakage"], info="Sensitive data this server touches.")
                edge(f"out:{n}", did, [r for r in leaks if f"Leaked {m} " in r["reason"]])
            called = [r for r in agent_rows if n in (r["response"] or "") + r["reason"]]
            if called:
                edges.append({"id": f"agent->{tid}", "source": "agent", "target": tid, "status": _status(called)})
        return {"kind": kind, "nodes": list(nodes.values()), "edges": edges}

    # chatbot / http: attack categories -> (endpoint ->) bot -> what it holds
    cats = list(dict.fromkeys(r["category"] for r in results))
    for c, x, y in col(cats, 0, 90):
        rows = [r for r in results if r["category"] == c]
        node(f"cat:{c}", CAT_LABEL.get(c, c), "attack", x, y, rows,
             problem=f"Your {noun} {PROBLEM.get(c, c)}.", fix=RULES.get(c, ""), info=EXPLAIN.get(c, ""))
    center = "bot"
    if kind == "http":
        url = (report.get("target", {}).get("endpoint") or {}).get("url") or ""
        u = urlparse(url)
        node("endpoint", u.netloc or "endpoint", "endpoint", 330, 0, info=f"The HTTP endpoint ({url or 'URL not recorded'}).")
        node("bot", f"POST {u.path or '/'}", "route", 600, 0, results, problem="This route returned protected data to an attacker.",
             fix="Harden the bot's system prompt (run GuardRail Lens on its YAML) and filter replies for secrets.",
             info="The chat route the attacks were sent to.")
        for c in cats:
            edge(f"cat:{c}", "endpoint", [r for r in results if r["category"] == c])
        edge("endpoint", "bot", results)
        x_assets = 900
    else:
        node("bot", report["target"]["name"], "target", 360, 0, info=report["target"].get("description", ""))
        for c in cats:
            edge(f"cat:{c}", "bot", [r for r in results if r["category"] == c])
        x_assets = 720

    # assets: system prompt, each secret, each PII record, policies
    def hits(pred):
        return [r for r in results if pred(r)]
    assets = [("asset:prompt", "System prompt", "prompt",
               hits(lambda r: "system prompt" in r["reason"].lower() or (r["category"] == "system_prompt_leak" and not LEAK_RE.search(r["reason"]))),
               "Its hidden instructions were revealed.", RULES["system_prompt_leak"], "The bot's hidden instructions.")]
    secrets = list(getattr(target, "secrets", []) or []) or sorted({m.group(2) for r in results for m in [LEAK_RE.search(r["reason"])] if m and m.group(1) == "secret"})
    for s in secrets:
        masked = s[:4] + "…" + s[-3:] if len(s) > 8 else s
        assets.append((f"asset:secret:{s}", f"Secret {masked}", "secret", hits(lambda r, s=s: f"'{s}'" in r["reason"]),
                       "This secret was given to an attacker.", RULES["secret_exfiltration"], "A canary secret that must never leak."))
    for rec in list(getattr(target, "pii", []) or []):
        name = rec.split(",")[0].strip()
        fields = [f.strip() for f in rec.split(",") if len(f.strip()) >= 5]
        assets.append((f"asset:pii:{name}", f"PII: {name}", "pii", hits(lambda r, fs=fields: any(f"'{f}'" in r["reason"] for f in fs)),
                       "This person's personal data was shared.", RULES["pii_exfiltration"], "A personal-data record the bot can see."))
    pols = list(getattr(target, "policies", []) or [])
    if pols:
        assets.append(("asset:policies", f"Policies ({len(pols)})", "policy",
                       hits(lambda r: r["category"] in ("roleplay_jailbreak", "instruction_override", "indirect_injection")),
                       "The bot was talked out of its rules.", RULES["instruction_override"], "; ".join(pols)[:300]))
    for (aid, label, typ, rows, prob, fix, info), x, y in col(assets, x_assets, 90):
        n = node(aid, label, typ, x, y, rows, problem=prob, fix=fix, info=info)
        if not rows:
            n.update(status="safe", stats="never leaked", problem=info)
        edge("bot", aid, rows)
    return {"kind": kind, "nodes": list(nodes.values()), "edges": edges}


def summary(report: dict) -> dict:
    """Compact, stable JSON for agents and CI."""
    b, a = report["before"]["score"], (report.get("after") or {}).get("score")
    return {
        "schema": SCHEMA, "target": report["target"]["name"], "kind": _kind(report), "mode": report.get("mode"),
        "score": b["overall"], "score_after_fix": a["overall"] if a else None,
        "attacks": b["attacks"], "leaks": b["leaks"], "partials": b["partials"], "errors": b["errors"],
        "verdict": verdict(report),
        "categories": {k: {"score": c["score"], "got_through": c["leaks"] + c["partials"], "attacks": c["attacks"]}
                       for k, c in b["categories"].items()},
        "findings": findings(report),
        "fix": {"hardened_system_prompt": report["patch"]["hardened_system_prompt"], "diff": report["patch"]["diff"]}
               if report.get("patch") else {"fixes": report.get("fixes", [])},
    }


def enrich(report: dict, target=None) -> dict:
    """Add verdict + map to a report (idempotent)."""
    report["verdict"] = verdict(report)
    report["map"] = surface_map(report, target)
    return report
