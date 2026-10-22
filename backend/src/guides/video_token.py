"""Video havolasi uchun qisqa muddatli imzo.

`<video src="...">` so'rovga Authorization header qo'sha olmaydi. Shuning uchun
ro'yxat (token bilan himoyalangan) har bir video uchun imzoli havola beradi:
`?token=<amal_qilish_muddati>.<hmac>`. Imzo yo'riqnoma id'siga bog'langan —
bitta videoning tokeni boshqasiga yaramaydi. Holat saqlanmaydi (Redis kerak emas).
"""

import hashlib
import hmac
import time
from uuid import UUID

from src.main.config import config


def _signature(guide_id: UUID, expires_at: int) -> str:
    message = f"edo-guide:{guide_id}:{expires_at}".encode()
    key = config.app.PROJECT_SECRET_KEY.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def make_video_token(guide_id: UUID) -> str:
    expires_at = int(time.time()) + config.app.GUIDE_VIDEO_URL_TTL_SECONDS
    return f"{expires_at}.{_signature(guide_id, expires_at)}"


def is_valid_video_token(guide_id: UUID, token: str) -> bool:
    expires_part, _, signature = token.partition(".")
    if not expires_part.isdigit() or not signature:
        return False
    expires_at = int(expires_part)
    if expires_at < time.time():
        return False
    return hmac.compare_digest(signature, _signature(guide_id, expires_at))
