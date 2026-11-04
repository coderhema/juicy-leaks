import json
from pathlib import Path

from juicy_leaks.cli import main
from juicy_leaks.config import Settings
from juicy_leaks.report import to_markdown
from juicy_leaks.scanner import scan
from juicy_leaks.targets import Target

EX = Path(__file__).resolve().parent.parent / "examples"


def test_full_mock_scan_improves_score():
    for name in ("bank_bot", "hr_bot", "travel_bot"):
        rep = scan(Target.from_yaml(EX / f"{name}.yaml"), Settings.load(mock=True), log=lambda *_: None)
        assert rep["mode"] == "mock"
        assert rep["before"]["score"]["attacks"] == 60
        assert rep["after"]["score"]["overall"] > rep["before"]["score"]["overall"]
        assert "+## Security rules" in rep["patch"]["diff"]
        assert "Worst transcripts" in to_markdown(rep)


def test_cli_writes_reports(tmp_path):
    assert main(["scan", "--target", str(EX / "bank_bot.yaml"), "--mock", "--out", str(tmp_path)]) == 0
    data = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert 0 <= data["before"]["score"]["overall"] <= 100
    assert next(tmp_path.glob("*.md")).read_text().startswith("# Juicy Leaks report")


def test_streamlit_app_runs_mock_scan(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(EX.parent)
    monkeypatch.setenv("JUICY_MOCK", "1")
    at = AppTest.from_file(str(EX.parent / "app.py"), default_timeout=60).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["report"]["before"]["score"]["overall"] is not None
    assert any("score-big" in m.value for m in at.markdown)


def test_streamlit_app_mcp_target_type(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(EX.parent)
    monkeypatch.setenv("JUICY_MOCK", "1")
    at = AppTest.from_file(str(EX.parent / "app.py"), default_timeout=90).run()
    at.radio[0].set_value("MCP server").run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["report"]["kind"] == "mcp"
    assert any("Hardened server" in m.value for m in at.markdown)
