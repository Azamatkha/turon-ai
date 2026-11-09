"""Oltin savollar bilan bot sifatini tekshirish.

Ishlayotgan backend'ga (lokal yoki server) haqiqiy so'rov yuboradi:
`POST /v1/chat/ask` (oqimsiz), javobni tests/golden/golden_questions.json
dagi kutilmalar bilan solishtiradi va hisobot chiqaradi. Model, prompt yoki
bilim bazasi o'zgargandan keyin ishga tushiring — nima buzilganini darhol
ko'rasiz.

Ishlatish (backend/ ichidan):
    TURON_API=http://localhost:8100 TURON_TOKEN=<access token> python scripts/golden_eval.py
    python scripts/golden_eval.py --only security,privacy --min 1.0
    python scripts/golden_eval.py --bootstrap 30   # admin token kerak

`--bootstrap N` — eng ko'p so'ralgan N ta savolni (admin statistikasi)
joriy javoblari bilan `tests/golden/golden_draft.json` ga yozadi. Undan
kutilmalarni (expect_*) qo'lda to'ldirib, asosiy faylga ko'chirasiz.

Token: brauzerda tizimga kirgach DevTools -> Application -> Local Storage
dagi access token. Token faylga yozilmaydi va hisobotga tushmaydi.
Chiqish kodi: o'tganlar ulushi `--min` dan past bo'lsa 1 (CI'da ishlatish mumkin).
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.utils.uzbek_script import to_latin  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "golden_questions.json"
DRAFT = ROOT / "tests" / "golden" / "golden_draft.json"
REPORTS = ROOT / "tests" / "golden" / "reports"

_APOS = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'"})


def _norm(text: str) -> str:
    """Solishtirish uchun: lotin, kichik harf, apostroflar bir xil."""
    return to_latin(text).translate(_APOS).lower()


def _script(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "none"
    cyr = sum(1 for c in letters if "Ѐ" <= c <= "ӿ")
    return "cyrillic" if cyr / len(letters) >= 0.5 else "latin"


def check(item: dict[str, Any], answer: str, sources: list[str]) -> list[str]:
    """Bajarilmagan kutilmalar ro'yxati (bo'sh — o'tdi)."""
    problems: list[str] = []
    ans = _norm(answer)
    for s in item.get("expect_all", []):
        if _norm(s) not in ans:
            problems.append(f"yo'q: {s!r}")
    anys = item.get("expect_any", [])
    if anys and not any(_norm(s) in ans for s in anys):
        problems.append(f"birortasi ham yo'q: {anys}")
    for s in item.get("forbid", []):
        # Taqiqlangan matn asl ko'rinishida ham, normallashganda ham qidiriladi
        if s in answer or _norm(s) in ans:
            problems.append(f"bo'lmasligi kerak edi: {s!r}")
    src = item.get("expect_source")
    if src and not any(_norm(src) in _norm(t) for t in sources):
        problems.append(f"manba yo'q: {src!r} (bor: {sources})")
    want = item.get("expect_script")
    if want and _script(answer) != want:
        problems.append(f"yozuv {_script(answer)}, kutilgan {want}")
    return problems


def _client(api: str, token: str) -> httpx.Client:
    # trust_env=False: lokal API korporativ proksi orqali ketmasin
    return httpx.Client(
        base_url=api.rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=300,
        trust_env=False,
    )


def run(api: str, token: str, only: set[str], minimum: float) -> int:
    data = json.loads(GOLDEN.read_text("utf-8"))
    items = [
        q for q in data["questions"]
        if q.get("enabled", True) and (not only or q.get("category") in only)
    ]
    if not items:
        print("Tekshiriladigan savol yo'q (filtr yoki enabled=false).")
        return 1

    results = []
    with _client(api, token) as client:
        for item in items:
            started = time.monotonic()
            try:
                res = client.post("/v1/chat/ask", json={"question": item["question"], "history": []})
                res.raise_for_status()
                body = res.json()
                answer = str(body.get("answer", ""))
                sources = [str(s.get("title", "")) for s in body.get("sources") or []]
                problems = check(item, answer, sources)
            except Exception as exc:  # noqa: BLE001 - bitta savol qolganlarini to'xtatmasin
                answer, sources, problems = "", [], [f"so'rov xatosi: {type(exc).__name__}: {exc}"]
            secs = time.monotonic() - started
            ok = not problems
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {item['id']:<42} {secs:5.1f}s")
            for p in problems:
                print(f"        - {p}")
            results.append({
                "id": item["id"], "category": item.get("category"), "question": item["question"],
                "passed": ok, "problems": problems, "seconds": round(secs, 1),
                "answer": answer, "sources": sources,
            })

    passed = sum(r["passed"] for r in results)
    rate = passed / len(results)
    print(f"\nNatija: {passed}/{len(results)} o'tdi ({rate:.0%}); talab: {minimum:.0%}")
    by_cat: dict[str, list[bool]] = {}
    for r in results:
        by_cat.setdefault(r["category"] or "-", []).append(r["passed"])
    for cat, vals in sorted(by_cat.items()):
        print(f"  {cat:<12} {sum(vals)}/{len(vals)}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    report = REPORTS / f"golden-{datetime.now():%Y%m%d-%H%M}.json"
    report.write_text(
        json.dumps({"api": api, "passed": passed, "total": len(results), "results": results},
                   ensure_ascii=False, indent=2),
        "utf-8",
    )
    print(f"Hisobot: {report}")
    return 0 if rate >= minimum else 1


def bootstrap(api: str, token: str, n: int) -> int:
    """Eng ko'p so'ralgan savollardan qoralama: kutilmalarni odam to'ldiradi."""
    with _client(api, token) as client:
        res = client.get("/v1/admin/questions", params={"days": 30, "limit": n})
        res.raise_for_status()
        top = res.json().get("top", [])
        draft = []
        for i, row in enumerate(top, 1):
            q = row["question"]
            ans = client.post("/v1/chat/ask", json={"question": q, "history": []}).json()
            draft.append({
                "id": f"draft-{i:02d}",
                "category": "product",
                "enabled": False,
                "question": q,
                "expect_any": [],
                "_asked_times": row.get("count"),
                "_current_answer": ans.get("answer", ""),
                "_current_sources": [s.get("title") for s in ans.get("sources") or []],
                "_todo": "Javob to'g'rimi? To'g'ri bo'lsa asosiy faktni expect_any/expect_all ga yozing",
            })
    DRAFT.write_text(json.dumps({"questions": draft}, ensure_ascii=False, indent=2), "utf-8")
    print(f"{len(draft)} ta qoralama: {DRAFT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Oltin savollar bilan bot sifatini tekshirish")
    parser.add_argument("--api", default=os.getenv("TURON_API", "http://localhost:8100"))
    parser.add_argument("--only", default="", help="kategoriyalar, vergul bilan: security,privacy")
    parser.add_argument("--min", type=float, default=0.9, help="o'tish ulushi chegarasi (0..1)")
    parser.add_argument("--bootstrap", type=int, default=0, help="TOP-N savoldan qoralama yasash")
    args = parser.parse_args()

    token = os.getenv("TURON_TOKEN", "").strip()
    if not token:
        print("TURON_TOKEN muhit o'zgaruvchisi kerak (access token).", file=sys.stderr)
        return 2
    if args.bootstrap:
        return bootstrap(args.api, token, args.bootstrap)
    only = {c.strip() for c in args.only.split(",") if c.strip()}
    return run(args.api, token, only, args.min)


if __name__ == "__main__":
    sys.exit(main())
