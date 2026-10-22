import time
from uuid import uuid4

import pytest

from src.core.errors.exceptions import UnauthorizedException
from src.guides.storage import looks_like_mp4 as _looks_like_mp4
from src.guides import video_token
from src.guides.usecases import GetGuideVideoUseCase
from tests.fakes.db import FakeAsyncSession, FakeUnitOfWork


def test_video_token_roundtrip() -> None:
    guide_id = uuid4()
    token = video_token.make_video_token(guide_id)
    assert video_token.is_valid_video_token(guide_id, token)


def test_video_token_bound_to_guide() -> None:
    token = video_token.make_video_token(uuid4())
    assert not video_token.is_valid_video_token(uuid4(), token)


def test_video_token_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    guide_id = uuid4()
    token = video_token.make_video_token(guide_id)
    future = time.time() + 10 * 24 * 60 * 60
    monkeypatch.setattr(video_token.time, "time", lambda: future)
    assert not video_token.is_valid_video_token(guide_id, token)


@pytest.mark.parametrize("token", ["", "abc", "123.", ".deadbeef", "1.2.3"])
def test_video_token_malformed(token: str) -> None:
    assert not video_token.is_valid_video_token(uuid4(), token)


def test_mp4_signature_check() -> None:
    assert _looks_like_mp4(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8)
    assert not _looks_like_mp4(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    assert not _looks_like_mp4(b"")


@pytest.mark.asyncio
async def test_get_video_rejects_bad_token(fake_session: FakeAsyncSession) -> None:
    uow = FakeUnitOfWork(session=fake_session, repositories={})
    with pytest.raises(UnauthorizedException):
        await GetGuideVideoUseCase(uow=uow).execute(guide_id=uuid4(), token="1.bad")


# --- Bo'laklab yuklash (guides/storage.py) -----------------------------------
from pathlib import Path

from src.core.errors.exceptions import (
    InstanceProcessingException,
    NotAcceptableException,
    PayloadTooLargeException,
)
from src.guides import storage

MP4_HEAD = b"\x00\x00\x00\x18ftypmp42"


@pytest.fixture
def media_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(storage, "media_root", lambda: tmp_path)
    return tmp_path


@pytest.mark.asyncio
async def test_chunked_upload_happy_path(media_dir: Path) -> None:
    upload_id = await storage.start_upload()
    first = MP4_HEAD + b"a" * 100
    received = await storage.append_chunk(upload_id, 0, first, max_total=10_000)
    received = await storage.append_chunk(upload_id, received, b"b" * 50, max_total=10_000)
    assert received == len(first) + 50

    relative, size = await storage.finalize_upload(upload_id)
    assert size == received
    assert relative.endswith(".mp4")
    assert (media_dir / relative).read_bytes() == first + b"b" * 50
    # vaqtinchalik fayl ko'chirildi
    assert not list((media_dir / storage.TMP_SUBDIR).glob("*.part"))


@pytest.mark.asyncio
async def test_chunk_with_wrong_offset_rejected(media_dir: Path) -> None:
    upload_id = await storage.start_upload()
    await storage.append_chunk(upload_id, 0, MP4_HEAD, max_total=10_000)
    # Qayta yuborilgan (takroriy) bo'lak — ikki marta yozilmasligi kerak
    with pytest.raises(InstanceProcessingException):
        await storage.append_chunk(upload_id, 0, MP4_HEAD, max_total=10_000)


@pytest.mark.asyncio
async def test_non_mp4_rejected_on_first_chunk(media_dir: Path) -> None:
    upload_id = await storage.start_upload()
    with pytest.raises(NotAcceptableException):
        await storage.append_chunk(upload_id, 0, b"\x89PNG\r\n\x1a\n" * 4, max_total=10_000)


@pytest.mark.asyncio
async def test_upload_over_limit_rejected(media_dir: Path) -> None:
    upload_id = await storage.start_upload()
    received = await storage.append_chunk(upload_id, 0, MP4_HEAD + b"x" * 40, max_total=60)
    with pytest.raises(PayloadTooLargeException):
        await storage.append_chunk(upload_id, received, b"y" * 20, max_total=60)
