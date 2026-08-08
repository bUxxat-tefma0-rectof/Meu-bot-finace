"""
Repositório base com operações comuns
"""

import logging
from typing import Optional, List, Dict, Any, TypeVar, Generic
from datetime import datetime

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from database.connection import get_db

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Repositório base com CRUD genérico"""
    
    def __init__(self, model: type[T]):
        self.model = model
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Busca por ID"""
        db = await get_db()
        try:
            result = await db.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Busca todos com paginação"""
        db = await get_db()
        try:
            result = await db.execute(
                select(self.model)
                .order_by(self.model.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def create(self, **kwargs) -> T:
        """Cria um novo registro"""
        db = await get_db()
        try:
            instance = self.model(**kwargs)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)
            return instance
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar {self.model.__name__}: {e}")
            raise
        finally:
            await db.close()
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Atualiza um registro"""
        db = await get_db()
        try:
            kwargs["updated_at"] = datetime.utcnow()
            await db.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**kwargs)
            )
            await db.commit()
            
            result = await db.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar {self.model.__name__}: {e}")
            raise
        finally:
            await db.close()
    
    async def delete(self, id: int) -> bool:
        """Remove um registro"""
        db = await get_db()
        try:
            await db.execute(
                delete(self.model).where(self.model.id == id)
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao deletar {self.model.__name__}: {e}")
            return False
        finally:
            await db.close()
    
    async def count(self, **filters) -> int:
        """Conta registros com filtros"""
        db = await get_db()
        try:
            query = select(func.count(self.model.id))
            
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            result = await db.execute(query)
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def exists(self, **filters) -> bool:
        """Verifica se existe registro com os filtros"""
        count = await self.count(**filters)
        return count > 0
