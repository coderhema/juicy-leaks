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


def test_cli_json_and_fail_under(tmp_path, capsys):
    from guardrail_lens.cli import main
    code = main(["scan", "--target", "examples/bank_bot.yaml", "--mock", "--mutations", "0",
                 "--out", str(tmp_path), "--json", "--fail-under", "90"])
    data = json.loads(capsys.readouterr().out)
    assert code == 3 and data["score"] < 90 and data["findings"]
    assert main(["scan", "--target", "examples/bank_bot.yaml", "--mock", "--mutations", "0",
                 "--out", str(tmp_path), "--fail-under", "0"]) == 0
