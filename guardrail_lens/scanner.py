"""Orchestrates a scan: attacks -> target -> judge -> score -> patch -> re-scan."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .attacks import CATEGORIES, Attack, builtin_attacks, mutate_attack
from .config import Settings
from .judge import judge
from .llm import ChatClient
from .patch import generate_patch, make_diff
from .targets import Target, build_target_runner


def _run_one(runner, target, attack: Attack, client, judge_model):
    t0 = time.time()
    try:
        response = runner.ask(attack.prompt)
        error = None
    except Exception as e:  # keep scanning even if one call fails
        response, error = "", str(e)
    v = None
    if not error:
        try:
            v = judge(response, target, attack.prompt, client, judge_model)
        except Exception as e:  # judge failed (e.g. rate limit): count as error, don't crash the scan
            error = f"judge: {e}"
    return {**attack.to_dict(), "response": response, "error": error,
            "verdict": v.verdict if v else "error", "severity": v.severity if v else 0,
            "reason": v.reason if v else error, "detector": v.detector if v else "-",
            "latency_s": round(time.time() - t0, 2)}


def score(results: list[dict], categories: dict | None = None) -> dict:
    valid = [r for r in results if r["verdict"] != "error"]
    n = len(valid) or 1
    # all calls failed -> no score (previously this showed a misleading 100/100)
    overall = round(100 * (1 - sum(r["severity"] for r in valid) / (10 * n))) if valid else None
    cats = {}
    for c, label in (categories or CATEGORIES).items():
        rs = [r for r in valid if r["category"] == c]
        if not rs:
            continue
        cats[c] = {"label": label, "attacks": len(rs),
                   "leaks": sum(r["verdict"] == "leak" for r in rs),
                   "partials": sum(r["verdict"] == "partial" for r in rs),
                   "score": round(100 * (1 - sum(r["severity"] for r in rs) / (10 * len(rs))))}
    return {"overall": overall, "attacks": len(results), "errors": len(results) - len(valid),
            "leaks": sum(r["verdict"] == "leak" for r in valid),
            "partials": sum(r["verdict"] == "partial" for r in valid), "categories": cats}


def run_attacks(target: Target, attacks: list[Attack], settings: Settings, client, workers: int, progress=None):
    runner = build_target_runner(target, settings, client)
    judge_client = None if settings.mock else client
    results = [None] * len(attacks)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = {pool.submit(_run_one, runner, target, a, judge_client, settings.judge_model): i
                for i, a in enumerate(attacks)}
        for done, fut in enumerate(futs, 1):
            results[futs[fut]] = fut.result()
            if progress:
                progress(done, len(attacks))
    return results


def scan(target: Target, settings: Settings, mutations: int = 1, categories: list[str] | None = None,
         limit: int | None = None, patch: bool = True, workers: int = 4, progress=None, log=print) -> dict:
    client = None if settings.mock else ChatClient(settings.api_key, settings.base_url, extra_body=settings.extra_body)
    attacks = builtin_attacks()
    if categories:
        attacks = [a for a in attacks if a.category in categories]
    if limit:
        attacks = attacks[:limit]
    if mutations > 0:
        log(f"Mutating {len(attacks)} attacks x{mutations} with the attacker LLM...")
        context = f"{target.name}: {target.description}"
        def _mut(a):
            try:
                return mutate_attack(a, client, settings.attacker_model, context, mutations)
            except Exception as e:
                log(f"  mutation failed for {a.id}: {e}")
                return []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            extra = [v for vs in pool.map(_mut, attacks) for v in vs]
        attacks = attacks + extra

    log(f"Running {len(attacks)} attacks against '{target.name}' (before)...")
    before = run_attacks(target, attacks, settings, client, workers, progress)
    report = {
        "tool": "GuardRail Lens", "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": {"name": target.name, "description": target.description,
                   "model": "mock" if settings.mock else (target.model or settings.target_model)},
        "mode": "mock" if settings.mock else "live",
        "models": {"provider": settings.provider, "target": settings.target_model, "attacker": settings.attacker_model,
                   "judge": settings.judge_model, "base_url": settings.base_url},
        "before": {"score": score(before), "results": before},
    }
    if patch and not target.endpoint:
        failures = [r for r in before if r["verdict"] in ("leak", "partial")]
        log(f"{len(failures)} attacks succeeded. Generating hardened system prompt...")
        hardened = generate_patch(target.system_prompt, failures, client, settings.attacker_model)
        log("Re-running attacks against the hardened prompt (after)...")
        after = run_attacks(target.with_system_prompt(hardened), attacks, settings, client, workers, progress)
        report["patch"] = {"hardened_system_prompt": hardened, "diff": make_diff(target.system_prompt, hardened)}
        report["after"] = {"score": score(after), "results": after}
    return report
