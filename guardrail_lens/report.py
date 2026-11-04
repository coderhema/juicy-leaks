"""Render scan reports as Markdown (JSON is written as-is)."""
from __future__ import annotations

import json
from pathlib import Path


def worst(results: list[dict], n: int = 5) -> list[dict]:
    bad = [r for r in results if r["verdict"] in ("leak", "partial")]
    return sorted(bad, key=lambda r: -r["severity"])[:n]


def _grade(s: int) -> str:
    return "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 60 else "D" if s >= 40 else "F"


def to_markdown(report: dict) -> str:
    b = report["before"]["score"]
    a = report.get("after", {}).get("score")
    out = [f"# GuardRail Lens report: {report['target']['name']}", "",
           f"_Generated {report['generated_at']} | mode: {report['mode']} | target model: {report['target']['model']}_", ""]
    if a:
        out += [f"**Safety score: {b['overall']}/100 ({_grade(b['overall'])}) -> {a['overall']}/100 ({_grade(a['overall'])}) after patch**", ""]
    else:
        out += [f"**Safety score: {b['overall']}/100 ({_grade(b['overall'])})**", ""]
    out += [f"{b['attacks']} attacks, {b['leaks']} leaks, {b['partials']} partial", "",
            "| Category | Attacks | Leaks | Partial | Score before | Score after |", "|---|---|---|---|---|---|"]
    for c, s in b["categories"].items():
        after = a["categories"].get(c, {}).get("score", "-") if a else "-"
        out.append(f"| {s['label']} | {s['attacks']} | {s['leaks']} | {s['partials']} | {s['score']} | {after} |")
    out += ["", "## Worst transcripts", ""]
    for r in worst(report["before"]["results"]):
        out += [f"### [{r['verdict'].upper()} sev {r['severity']}] {r['name']} ({r['category']})", "",
                f"_{r['reason']}_ (detector: {r['detector']})", "", "**Attack:**", "```", r["prompt"], "```",
                "**Reply:**", "```", r["response"][:800], "```", ""]
    if "patch" in report:
        out += ["## Suggested patch", "", "```diff", report["patch"]["diff"], "```", ""]
    return "\n".join(out)


def write_reports(report: dict, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = report["target"]["name"].lower().replace(" ", "_")
    jp, mp = out / f"{slug}_report.json", out / f"{slug}_report.md"
    jp.write_text(json.dumps(report, indent=2))
    mp.write_text(to_markdown(report))
    return jp, mp
