"""Audit amallari nomlari — frontend tarjimalari ham shu kalitlarga tayanadi."""

from enum import StrEnum


class AuditAction(StrEnum):
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    KNOWLEDGE_UPLOAD = "knowledge.upload"
    KNOWLEDGE_UPDATE = "knowledge.update"
    KNOWLEDGE_DELETE = "knowledge.delete"
    KNOWLEDGE_PDF = "knowledge.pdf"
    KNOWLEDGE_EMPLOYEES = "knowledge.employees"
    KNOWLEDGE_SCRAPE = "knowledge.scrape"
    KNOWLEDGE_VALIDITY = "knowledge.validity"
    KNOWLEDGE_META = "knowledge.meta"
    KNOWLEDGE_CATEGORY = "knowledge.category"
    KNOWLEDGE_RESCRAPE = "knowledge.rescrape"

    REPORT_UPDATE = "report.update"

    GUIDE_CREATE = "guide.create"
    GUIDE_UPDATE = "guide.update"
    GUIDE_DELETE = "guide.delete"

    ANSWER_REVIEW = "answer.review"
    ANSWER_MESSAGE = "answer.message"

    BACKUP_RUN = "backup.run"


# Jurnalga YOZILMAYDIGAN mayda amallar (admin so'rovi, 2026-11-20): turkum va
# izoh qo'yish, turkumlar ro'yxatini tahrirlash, foydalanuvchini tahrirlash.
# Ular juda ko'p bo'lib, muhim amallarni (o'chirish, yuklash) ko'mib yuborardi.
# Avval yozilganlari ham ro'yxatda ko'rsatilmaydi.
SKIPPED_ACTIONS = frozenset(
    {
        AuditAction.KNOWLEDGE_META,
        AuditAction.KNOWLEDGE_CATEGORY,
        AuditAction.USER_UPDATE,
    }
)

# details'ga qiymati yozilmaydigan maydonlar: sirlar va shaxsiy ma'lumot.
# Jurnalda faqat "maydon o'zgardi" ko'rinadi ("***").
SECRET_FIELDS = frozenset(
    {
        "password",
        "new_password",
        "old_password",
        "token",
        "pnfl",
        "doc_seria",
        "doc_number",
        "birth_date",
    }
)
