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
    KNOWLEDGE_RESCRAPE = "knowledge.rescrape"

    REPORT_UPDATE = "report.update"

    GUIDE_CREATE = "guide.create"
    GUIDE_UPDATE = "guide.update"
    GUIDE_DELETE = "guide.delete"

    ANSWER_REVIEW = "answer.review"

    BACKUP_RUN = "backup.run"


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
