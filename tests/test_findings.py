import json

from guardrail_lens.findings import summary


def _load(name):
    from guardrail_lens.config import Settings
    from guardrail_lens.scanner import scan
    from guardrail_lens.targets import Target
    return scan(Target.from_yaml(f"examples/{name}.yaml"), Settings.load(mock=True), mutations=0)


def test_verdict_and_map_chatbot():
    r = _load("bank_bot")
    assert r["verdict"].startswith("Your bot ") and "score from" in r["verdict"]
    ids = {n["id"]: n for n in r["map"]["nodes"]}
    assert ids["asset:secret:VIP-NAIRA-7781"]["status"] == "leak"
    assert any(e["status"] == "leak" for e in r["map"]["edges"])
    s = summary(r)
    assert s["schema"] == "guardrail-lens/findings@1" and s["findings"][0]["fix"]
    json.dumps(s)
