"""Savolda "xodim" so'zi bor, lekin router uni xodim haqida emas deb bilgan —
"xodim topilmadi" o'rniga bilim bazasidan javob."""

from src.knowledge.router import Intent, Route
from src.knowledge.usecases import _drop_unwanted_employee_route

Q = "bank xodimlari nima qilsa mukofotlanadi"


def test_not_found_dropped_when_router_says_product() -> None:
    product = Route(Intent.PRODUCT, "xodimlarni mukofotlash shartlari")
    assert _drop_unwanted_employee_route(("none", []), product, Q) is None
    assert _drop_unwanted_employee_route(("ask", []), product, Q) is None


def test_employee_router_or_found_kept() -> None:
    employee = Route(Intent.EMPLOYEE, "")
    product = Route(Intent.PRODUCT, "")
    assert _drop_unwanted_employee_route(("none", []), employee, Q) == ("none", [])
    # Xodim TOPILDI yoki IP egasi so'raldi — o'zgarmaydi
    found = ("answer", [{"fish": "A"}])
    assert _drop_unwanted_employee_route(found, product, Q) == found
    assert _drop_unwanted_employee_route(("no_ip", []), product, Q) == ("no_ip", [])
    # Router yiqilgan — avvalgidek
    assert _drop_unwanted_employee_route(("none", []), None, Q) == ("none", [])
