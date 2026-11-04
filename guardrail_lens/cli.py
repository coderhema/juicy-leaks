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
    s.add_argument("--target", required=True, help="Path to target YAML (see examples/)")
    s.add_argument("--mock", action="store_true", help="Offline mode with canned responses (no API key)")
    s.add_argument("--live", action="store_true", help="Force live mode (requires the provider API key)")
    s.add_argument("--provider", choices=list(PROVIDERS), help="LLM provider (default nvidia, or LLM_PROVIDER env)")
    s.add_argument("--model", help="Model for target/attacker/judge (default per provider, e.g. meta/llama-3.3-70b-instruct)")
    s.add_argument("--base-url", help="Override the OpenAI-compatible base URL")
    s.add_argument("--mutations", type=int, default=1, help="Attacker-LLM variants per template (default 1)")
    s.add_argument("--category", action="append", choices=list(CATEGORIES), help="Only run these categories")
    s.add_argument("--limit", type=int, help="Only run the first N templates")
    s.add_argument("--no-patch", action="store_true", help="Skip hardened prompt + re-run")
    s.add_argument("--workers", type=int, default=3, help="Parallel requests (lower if rate limited)")
    s.add_argument("--out", default="reports", help="Output directory")
    sub.add_parser("attacks", help="List the built-in attack templates")
    args = p.parse_args(argv)

    if args.cmd == "attacks":
        from .attacks import builtin_attacks
        for a in builtin_attacks():
            print(f"{a.id:28} {a.name}")
        return 0

    mock = True if args.mock else (False if args.live else None)
    settings = Settings.load(mock=mock, model=args.model, base_url=args.base_url, provider=args.provider)
    if not settings.mock and not settings.api_key:
        print(f"{settings.key_env} is not set. Add it to .env or use --mock.", file=sys.stderr)
        return 2
    if settings.mock and not args.mock:
        print(f"No {settings.key_env} found: running in --mock mode.")
    target = Target.from_yaml(args.target)
    report = scan(target, settings, mutations=args.mutations, categories=args.category,
                  limit=args.limit, patch=not args.no_patch, workers=args.workers)
    b = report["before"]["score"]
    print(f"\nSafety score: {b['overall']}/100  ({b['leaks']} leaks, {b['partials']} partial of {b['attacks']})")
    for c in b["categories"].values():
        bar = "#" * (c["score"] // 5)
        print(f"  {c['label']:38} {c['score']:3}  {bar}")
    if "after" in report:
        print(f"After patch:  {report['after']['score']['overall']}/100")
    jp, mp = write_reports(report, args.out)
    print(f"\nReport: {mp}\nJSON:   {jp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
