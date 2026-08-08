"""
Repositório de Notificações
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, and_

from database.models.notification import Notification
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class NotificationRepository(BaseRepository[Notification]):
    """Repositório para notificações"""
    
    def __init__(self):
        super().__init__(Notification)
    
    async def get_pending_notifications(self, limit: int = 10) -> List[Notification]:
        """Notificações pendentes de envio"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Notification)
                .where(Notification.is_sent == False)
                .order_by(Notification.id)
                .limit(limit)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_notifications_by_type(
        self,
        notification_type: str,
        limit: int = 20,
    ) -> List[Notification]:
        """Notificações por tipo"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Notification)
                .where(Notification.type == notification_type)
                .order_by(Notification.id.desc())
                .limit(limit)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[Notification]:
        """Notificações relacionadas a um usuário"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Notification)
                .where(Notification.related_user_id == user_id)
                .order_by(Notification.id.desc())
                .limit(limit)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def mark_as_sent(
        self,
        notification_id: int,
        message_id: int = None,
    ) -> bool:
        """Marca notificação como enviada"""
        return await self.update(
            notification_id,
            is_sent=True,
            sent_at=datetime.utcnow(),
            message_id=message_id,
        ) is not None
    
    async def mark_all_as_sent(self):
        """Marca todas como enviadas"""
        db = await get_db()
        try:
            from sqlalchemy import update
            await db.execute(
                update(Notification)
                .where(Notification.is_sent == False)
                .values(is_sent=True, sent_at=datetime.utcnow())
            )
            await db.commit()
        finally:
            await db.close()
    
    async def delete_old_notifications(self, days: int = 30) -> int:
        """Remove notificações antigas"""
        db = await get_db()
        try:
            from datetime import timedelta
            from sqlalchemy import delete
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute(
                delete(Notification)
                .where(
                    and_(
                        Notification.created_at < cutoff,
                        Notification.is_sent == True,
                    )
                )
            )
            await db.commit()
            
            return result.rowcount
        except Exception as e:
            await db.rollback()
            return 0
        finally:
            await db.close()
