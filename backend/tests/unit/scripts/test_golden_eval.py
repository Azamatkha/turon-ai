"""Oltin savollar skriptining baholash mantiqi (tarmoqsiz) va to'plam fayli."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("golden_eval", ROOT / "scripts" / "golden_eval.py")
assert _spec and _spec.loader
golden_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden_eval)


def test_expect_any_ignores_script_and_case() -> None:
    item = {"expect_any": ["Qaysi xodim"]}
    assert golden_eval.check(item, "ҚАЙСИ ХОДИМ ҳақида маълумот керак?", []) == []


def test_forbid_and_expect_all() -> None:
    item = {"expect_all": ["22%"], "forbid": ["4111 1111 1111 1111"]}
    problems = golden_eval.check(item, "Karta 4111 1111 1111 1111", [])
    assert any("yo'q" in p for p in problems)
    assert any("bo'lmasligi" in p for p in problems)


def test_expect_source_and_script() -> None:
    item = {"expect_source": "Ta'lim", "expect_script": "cyrillic"}
    assert golden_eval.check(item, "Кредит фоизи", ["Ta’lim krediti"]) == []
    problems = golden_eval.check(item, "Kredit foizi", ["Ipoteka"])
    assert len(problems) == 2


def test_golden_file_is_valid() -> None:
    data = json.loads((ROOT / "tests" / "golden" / "golden_questions.json").read_text("utf-8"))
    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "id takrorlanmasin"
    allowed = {"id", "category", "question", "enabled", "expect_all", "expect_any",
               "forbid", "expect_source", "expect_script"}
    for q in data["questions"]:
        assert q["question"].strip()
        unknown = {k for k in q if not k.startswith("_")} - allowed
        assert not unknown, f"{q['id']}: noma'lum maydon {unknown}"
        if q.get("expect_script"):
            assert q["expect_script"] in {"cyrillic", "latin"}
