"""
Repositório de Sessões
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select

from database.models.user_session import UserSession
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[UserSession]):
    """Repositório para sessões de usuário"""
    
    def __init__(self):
        super().__init__(UserSession)
    
    async def get_by_user_id(self, user_id: int) -> Optional[UserSession]:
        """Busca sessão pelo ID do usuário"""
        db = await get_db()
        try:
            result = await db.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def delete_old_sessions(self, cutoff: datetime) -> int:
        """Remove sessões antigas"""
        db = await get_db()
        try:
            from sqlalchemy import delete
            result = await db.execute(
                delete(UserSession).where(UserSession.last_activity < cutoff)
            )
            await db.commit()
            return result.rowcount
        except Exception as e:
            await db.rollback()
            return 0
        finally:
            await db.close()
