"""Redis-backed status store for background PDF processing.

PDF (skanerlangan hujjat) OCR + LLM tozalash daqiqalab ketadi — korporativ
proxy esa so'rovni 60 soniyada uzadi. Shuning uchun yuklash Celery ishchisiga
o'tkaziladi: HTTP so'rovi darrov `job_id` qaytaradi, frontend esa holaatni shu
yerdan (Redis) so'rab turadi.

Kalitlar (TTL 1 soat):
- pdfjob:{id}        -> holat JSON (state, message, natija maydonlari)
- pdfjob:{id}:data   -> PDF baytlari base64 (ishchi o'qib olgach o'chiriladi)
"""

import json
from typing import Any

from redis.asyncio import Redis

JOB_TTL_SECONDS = 3600
_PREFIX = "pdfjob"


def _status_key(job_id: str) -> str:
    return f"{_PREFIX}:{job_id}"


def _data_key(job_id: str) -> str:
    return f"{_PREFIX}:{job_id}:data"


async def save_pdf(redis: Redis, job_id: str, pdf_b64: str) -> None:
    await redis.set(_data_key(job_id), pdf_b64, ex=JOB_TTL_SECONDS)


async def load_pdf(redis: Redis, job_id: str) -> str | None:
    value = await redis.get(_data_key(job_id))
    return str(value) if value is not None else None


async def clear_pdf(redis: Redis, job_id: str) -> None:
    """Ishchi PDF baytlarini o'qib bo'lgach — Redis'da katta base64 qolib
    ketmasin (holat esa TTL tugaguncha turadi)."""
    await redis.delete(_data_key(job_id))


async def get_status(redis: Redis, job_id: str) -> dict[str, Any] | None:
    raw = await redis.get(_status_key(job_id))
    if raw is None:
        return None
    result: dict[str, Any] = json.loads(raw)
    return result


async def set_status(redis: Redis, job_id: str, **fields: Any) -> None:
    """Holatni yangilaydi — mavjud maydonlar ustiga qo'shib yozadi (masalan
    faqat `state` ni o'zgartirish uchun)."""
    current = await get_status(redis, job_id) or {}
    current.update(fields)
    await redis.set(_status_key(job_id), json.dumps(current), ex=JOB_TTL_SECONDS)
