"""Chat suhbatlari/xabarlari mantig'i (foydalanuvchiga bog'langan)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.chats.models import ChatMessage, ChatSession
from src.core.errors.exceptions import InstanceNotFoundException


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sessions(self, user_id: UUID) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_session(self, user_id: UUID, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title or "")
        self._session.add(session)
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def get_session(self, user_id: UUID, session_id: UUID) -> ChatSession:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        session = (await self._session.execute(stmt)).scalar_one_or_none()
        if session is None:
            raise InstanceNotFoundException("Suhbat topilmadi")
        return session

    async def rename_session(
        self, user_id: UUID, session_id: UUID, title: str
    ) -> ChatSession:
        session = await self.get_session(user_id, session_id)
        session.title = title.strip()[:200]
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def delete_session(self, user_id: UUID, session_id: UUID) -> None:
        session = await self.get_session(user_id, session_id)
        await self._session.delete(session)
        await self._session.commit()

    async def add_message(
        self, user_id: UUID, session_id: UUID, role: str, content: str
    ) -> ChatMessage:
        session = await self.get_session(user_id, session_id)
        message = ChatMessage(session_id=session.id, role=role, content=content)
        self._session.add(message)
        # Birinchi foydalanuvchi xabari sarlavha bo'lib qoladi
        if role == "user" and not session.title:
            session.title = content[:60]
        await self._session.commit()
        await self._session.refresh(message)
        return message
