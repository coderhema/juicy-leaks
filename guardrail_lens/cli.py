"""guardrail-lens command line interface."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .attacks import CATEGORIES
from .config import PROVIDERS, Settings
from .report import write_reports
from .scanner import scan
from .targets import Target


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="guardrail-lens", description="Red-team your chatbot with Llama.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="Attack a target bot and score it")
    s.add_argument("--target", help="Path to target YAML: chatbot, http or mcp (see examples/)")
    s.add_argument("--url", help="Quick HTTP target: chatbot endpoint URL (POST JSON)")
    s.add_argument("--body-field", default="message", help="Request JSON field for --url (default message)")
    s.add_argument("--response-field", default="reply", help="Dotted response path for --url (default reply)")
    s.add_argument("--secret", action="append", default=[], help="Canary string to detect (repeatable)")
    s.add_argument("--compare", help="MCP: second target YAML (hardened server) to scan as 'after'")
    s.add_argument("--no-agent", action="store_true", help="MCP: skip the LLM agent loop")
    s.add_argument("--mock", action="store_true", help="Offline mode with canned responses (no API key)")
    s.add_argument("--live", action="store_true", help="Force live mode (requires the provider API key)")
    s.add_argument("--provider", choices=list(PROVIDERS), help="LLM provider (default nvidia, or LLM_PROVIDER env)")
    s.add_argument("--model", help="Model for target/attacker/judge (default per provider, e.g. meta/muse-glimmer-30b)")
    s.add_argument("--base-url", help="Override the OpenAI-compatible base URL")
    s.add_argument("--mutations", type=int, default=1, help="Attacker-LLM variants per template (default 1)")
    s.add_argument("--category", action="append", choices=list(CATEGORIES), help="Only run these categories")
    s.add_argument("--limit", type=int, help="Only run the first N templates")
    s.add_argument("--no-patch", action="store_true", help="Skip hardened prompt + re-run")
    s.add_argument("--workers", type=int, default=3, help="Parallel requests (lower if rate limited)")
    s.add_argument("--out", default="reports", help="Output directory")
    s.add_argument("--json", action="store_true", help="Print machine-readable findings (guardrail-lens/findings@1) to stdout")
    s.add_argument("--fail-under", type=int, metavar="SCORE",
                   help="CI: exit 3 if the target's score (before any fix) is below SCORE")
    sub.add_parser("attacks", help="List the built-in attack templates")
    args = p.parse_args(argv)

    if args.cmd == "attacks":
        from .attacks import builtin_attacks
        for a in builtin_attacks():
            print(f"{a.id:28} {a.name}")
        return 0

    out = sys.stdout
    if args.json:  # keep stdout clean for JSON; human output goes to stderr
        sys.stdout = sys.stderr
    try:
        code, report = _scan(p, args)
    finally:
        sys.stdout = out
    if report is not None:
        if args.json:
            import json
            from .findings import summary
            print(json.dumps(summary(report), indent=2))
        b = report["before"]["score"]["overall"]
        if code == 0 and args.fail_under is not None and b is not None and b < args.fail_under:
            print(f"Score {b} is below --fail-under {args.fail_under}.", file=sys.stderr)
            return 3
    return code


def _scan(p, args):
    mock = True if args.mock else (False if args.live else None)
    settings = Settings.load(mock=mock, model=args.model, base_url=args.base_url, provider=args.provider)
    if not settings.mock and not settings.api_key:
        print(f"{settings.key_env} is not set. Add it to .env or use --mock.", file=sys.stderr)
        return 2, None
    if settings.mock and not args.mock:
        print(f"No {settings.key_env} found: running in --mock mode.")
    if args.url:
        target = Target.from_dict({"name": args.url, "type": "http", "secrets": args.secret,
                                   "endpoint": {"url": args.url, "body_field": args.body_field,
                                                "response_field": args.response_field}})
    elif args.target:
        target = Target.from_yaml(args.target)
        target.secrets += args.secret
    else:
        p.error("scan needs --target FILE or --url URL")
    if target.type == "mcp":
        from .mcp_scan import scan_mcp
        compare = Target.from_yaml(args.compare) if args.compare else None
        report = scan_mcp(target, settings, agent=not args.no_agent, compare=compare)
    else:
        report = scan(target, settings, mutations=args.mutations, categories=args.category,
                      limit=args.limit, patch=not args.no_patch, workers=args.workers)
    b = report["before"]["score"]
    if b["overall"] is None:
        first = next((r["error"] for r in report["before"]["results"] if r["error"]), "")
        print(f"\nAll {b['attacks']} attacks errored, no score. First error: {first[:300]}", file=sys.stderr)
        return 1, report
    if b["errors"]:
        print(f"Warning: {b['errors']} of {b['attacks']} attacks errored and were excluded from the score.")
    print(f"\nSafety score: {b['overall']}/100  ({b['leaks']} leaks, {b['partials']} partial of {b['attacks']})")
    for c in b["categories"].values():
        bar = "#" * (c["score"] // 5)
        print(f"  {c['label']:38} {c['score']:3}  {bar}")
    if "after" in report:
        label = "Hardened server" if report.get("kind") == "mcp" else "After patch"
        print(f"{label}:  {report['after']['score']['overall']}/100")
    for f in report.get("fixes", [])[:8]:
        print(f"  fix [{f['where']}]: {f['fix']}")
    jp, mp = write_reports(report, args.out)
    print(f"\nReport: {mp}\nJSON:   {jp}")
    return 0, report


if __name__ == "__main__":
    raise SystemExit(main())
