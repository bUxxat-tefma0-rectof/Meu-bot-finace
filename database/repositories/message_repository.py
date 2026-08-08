"""
Repositório de Mensagens/Templates
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select

from database.models.message_template import MessageTemplate
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository[MessageTemplate]):
    """Repositório para templates de mensagens"""
    
    def __init__(self):
        super().__init__(MessageTemplate)
    
    async def get_by_key(self, key: str) -> Optional[MessageTemplate]:
        """Busca template pela chave"""
        db = await get_db()
        try:
            result = await db.execute(
                select(MessageTemplate)
                .where(MessageTemplate.key == key)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_all_messages(self) -> List[MessageTemplate]:
        """Busca todos os templates"""
        db = await get_db()
        try:
            result = await db.execute(
                select(MessageTemplate).order_by(MessageTemplate.key)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def upsert_message(
        self,
        key: str,
        name: str,
        content: str,
        description: str = None,
    ) -> MessageTemplate:
        """Cria ou atualiza template"""
        db = await get_db()
        try:
            existing = await db.execute(
                select(MessageTemplate).where(MessageTemplate.key == key)
            )
            template = existing.scalar_one_or_none()
            
            if template:
                template.content = content
                template.name = name
                template.updated_at = datetime.utcnow()
                if description:
                    template.description = description
            else:
                template = MessageTemplate(
                    key=key,
                    name=name,
                    content=content,
                    description=description,
                )
                db.add(template)
            
            await db.commit()
            await db.refresh(template)
            
            return template
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def delete_by_key(self, key: str) -> bool:
        """Remove template pela chave"""
        db = await get_db()
        try:
            template = await self.get_by_key(key)
            if template:
                await db.delete(template)
                await db.commit()
                return True
            return False
        except Exception as e:
            await db.rollback()
            return False
        finally:
            await db.close()
