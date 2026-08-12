"""Foydalanuvchi domeniga oid umumiy konstantalar.

Bank xodimlari email bilan ro'yxatdan o'tmaydi — ular faqat LOGIN kiritadi.
Lekin `users.email` ustuni template'dan qolgan va u NOT NULL + unique.
Shuning uchun email login'dan HOSIL QILINADI: `ali.valiyev@turonbank.uz`.

Bu qoida uchta joyda kerak bo'ladi (ro'yxatdan o'tish, admin foydalanuvchi
yaratishi, login o'zgartirilganda) — shuning uchun bitta joyda turadi.
Ilgari `EMAIL_DOMAIN` ikkita use-case ichida alohida yozilgan edi; domen
o'zgarsa, biri yangilanib ikkinchisi eskirib qolish xavfi bor edi.
"""

EMAIL_DOMAIN = "turonbank.uz"


def build_email(username: str) -> str:
    """Login'dan ichki email hosil qiladi."""
    return f"{username}@{EMAIL_DOMAIN}"


def split_full_name(full_name: str) -> tuple[str, str]:
    """"Ali Valiyev" -> ("Ali", "Valiyev").

    Bitta so'z kiritilsa familiya bo'sh qoladi (`last_name` NOT NULL bo'lgani
    uchun `None` emas, bo'sh satr). Ikkitadan ko'p so'z bo'lsa, qolgani
    familiyaga qo'shiladi: "Ali Valiyev O'g'li" -> ("Ali", "Valiyev O'g'li").
    """
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name
