from datetime import date

from src.knowledge.validity import (
    EXPIRED_PENALTY,
    WARN_DAYS,
    expiry_events,
    is_expired,
    penalize_expired,
)

TODAY = date(2026, 11, 9)


def test_is_expired_boundaries() -> None:
    # valid_until — oxirgi amal qiladigan kun: o'sha kuni hali amalda
    assert not is_expired({"valid_until": "2026-11-09"}, on=TODAY)
    assert is_expired({"valid_until": "2026-11-08"}, on=TODAY)
    assert not is_expired({}, on=TODAY)
    assert not is_expired({"valid_until": None}, on=TODAY)
    assert not is_expired({"valid_until": "noto'g'ri"}, on=TODAY)


def test_penalize_expired_reorders(monkeypatch) -> None:
    monkeypatch.setattr("src.knowledge.validity.today", lambda: TODAY)
    old = {"title": "Eski", "valid_until": "2026-01-01"}
    new = {"title": "Yangi"}
    out = penalize_expired([(old, 0.80), (new, 0.75)])
    assert [p["title"] for p, _ in out] == ["Yangi", "Eski"]
    assert out[1][1] == 0.80 * EXPIRED_PENALTY


def test_penalize_without_expired_is_noop() -> None:
    results = [({"title": "A"}, 0.9), ({"title": "B"}, 0.5)]
    assert penalize_expired(results) is results


def test_expiry_events_only_on_exact_days() -> None:
    payloads = [
        {"title": "Yaqin", "valid_until": "2026-11-16"},       # +7 kun
        {"title": "Yaqin", "valid_until": "2026-11-16"},       # bo'lak — takror
        {"title": "Tugadi", "valid_until": "2026-11-08"},      # kecha oxirgi kun
        {"title": "Uzoq", "valid_until": "2026-12-31"},
        {"title": "Allaqachon", "valid_until": "2026-10-01"},  # avval xabar berilgan
        {"title": "Muddatsiz"},
    ]
    soon, expired = expiry_events(payloads, on=TODAY)
    assert WARN_DAYS == 7
    assert soon == ["Yaqin"]
    assert expired == ["Tugadi"]
