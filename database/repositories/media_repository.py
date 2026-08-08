"""
Repositório de Mídia
"""

import logging
from typing import Optional, List

from sqlalchemy import select, and_

from database.models.media import Media
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class MediaRepository(BaseRepository[Media]):
    """Repositório para arquivos de mídia"""
    
    def __init__(self):
        super().__init__(Media)
    
    async def get_by_file_id(self, file_id: str) -> Optional[Media]:
        """Busca mídia pelo File ID do Telegram"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Media).where(Media.file_id == file_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_by_category(
        self,
        media_category: str,
        limit: int = 50,
    ) -> List[Media]:
        """Busca mídias por categoria"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Media)
                .where(
                    and_(
                        Media.media_category == media_category,
                        Media.is_active == True,
                    )
                )
                .order_by(Media.id.desc())
                .limit(limit)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_by_related(
        self,
        related_type: str,
        related_id: int,
    ) -> Optional[Media]:
        """Busca mídia relacionada a um item"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Media)
                .where(
                    and_(
                        Media.related_type == related_type,
                        Media.related_id == related_id,
                        Media.is_active == True,
                    )
                )
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def deactivate_media(self, media_id: int) -> bool:
        """Desativa uma mídia (soft delete)"""
        return await self.update(media_id, is_active=False) is not None
    
    async def get_all_active(self) -> List[Media]:
        """Todas as mídias ativas"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Media)
                .where(Media.is_active == True)
                .order_by(Media.id.desc())
            )
            return result.scalars().all()
        finally:
            await db.close()
