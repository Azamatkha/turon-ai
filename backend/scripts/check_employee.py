"""Diagnostika: xodim ma'lumoti vektor bazada bormi va qanday saqlangan?

"2206 kimniki" kabi savol javobsiz qolganda — muammo qidiruv mantig'idami
yoki ma'lumotning o'zi bazada yo'qmi, shuni ANIQ ko'rsatadi.

Ishlatish (app konteyneri ichida):

    python scripts/check_employee.py 2206
    python scripts/check_employee.py Xamdamboyev
    python scripts/check_employee.py "IT DEPARTAMENT"
    python scripts/check_employee.py            # umumiy holat

Chiqishi:
  * kolleksiyadagi umumiy nuqtalar soni;
  * doc_type=employee bo'yicha topilgan xodimlar soni (scroll filtri
    ishlayotganini tekshiradi);
  * bo'limlar ro'yxati va har birida nechtadan xodim borligi;
  * so'ralgan qiymat bo'yicha aniq mosliklar (ip / fish / department).
"""

import asyncio
import sys

from src.core.vectorstore.qdrant_store import QdrantStore


def _row(p: dict[str, object]) -> str:
    return (
        f"    ip={p.get('ip')!r:>10}  "
        f"dept={str(p.get('department'))[:28]:<28}  "
        f"{p.get('fish')}"
    )


async def main() -> None:
    needle = " ".join(sys.argv[1:]).strip()
    store = QdrantStore()

    if not await store.exists():
        print("XATO: Qdrant kolleksiyasi umuman yo'q.")
        return

    total = await store.count()
    print(f"Kolleksiyadagi umumiy nuqtalar: {total}")

    emps = await store.scroll_by_field("doc_type", "employee")
    print(f"doc_type=employee bo'yicha topilgan xodimlar: {len(emps)}")
    if not emps:
        print(
            "\nDIQQAT: xodimlar umuman topilmadi. Excel yuklanmagan yoki\n"
            "doc_type maydoni boshqacha yozilgan bo'lishi mumkin."
        )
        return

    depts: dict[str, int] = {}
    for p in emps:
        depts[str(p.get("department", ""))] = (
            depts.get(str(p.get("department", "")), 0) + 1
        )
    print(f"\nBo'limlar ({len(depts)} ta):")
    for d, n in sorted(depts.items()):
        print(f"    {n:>4}  {d}")

    no_ip = sum(1 for p in emps if not str(p.get("ip", "")).strip())
    dotted = [p for p in emps if "." in str(p.get("ip", ""))]
    print(f"\nIP maydoni bo'sh bo'lgan xodimlar: {no_ip}")
    print(f"IP'da nuqta bor ('2206.0' kabi): {len(dotted)}")
    for p in dotted[:5]:
        print(_row(p))
    if dotted:
        print(
            "    ^ Bu Excel float xatosi. Tuzatish kuchga kirishi uchun\n"
            "      xodimlar ro'yxatini admin paneldan QAYTA YUKLANG."
        )

    if not needle:
        return

    print(f"\n--- '{needle}' bo'yicha qidiruv ---")

    exact_ip = [p for p in emps if str(p.get("ip", "")).strip() == needle]
    print(f"ip aynan teng: {len(exact_ip)}")
    for p in exact_ip:
        print(_row(p))

    # Qdrant payload filtri (ilova aynan shu yo'lni zaxira sifatida ishlatadi)
    by_field = [
        p
        for p in await store.search_by_field("ip", needle, limit=60)
        if p.get("doc_type") == "employee"
    ]
    print(f"Qdrant payload filtri (ip={needle!r}): {len(by_field)}")
    for p in by_field:
        print(_row(p))

    low = needle.lower()
    in_name = [p for p in emps if low in str(p.get("fish", "")).lower()]
    print(f"F.I.SH ichida uchraydi: {len(in_name)}")
    for p in in_name[:20]:
        print(_row(p))

    in_dept = [p for p in emps if low in str(p.get("department", "")).lower()]
    print(f"Bo'lim nomida uchraydi: {len(in_dept)}")
    for p in in_dept[:20]:
        print(_row(p))


if __name__ == "__main__":
    asyncio.run(main())
