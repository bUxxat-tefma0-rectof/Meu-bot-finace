"""
Repositório de Categorias
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, and_, func

from database.models.category import Category
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class CategoryRepository(BaseRepository[Category]):
    """Repositório para categorias de produtos"""
    
    def __init__(self):
        super().__init__(Category)
    
    async def get_active_categories(self) -> List[Category]:
        """Categorias ativas ordenadas por posição"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Category)
                .where(Category.is_active == True)
                .order_by(Category.position, Category.name)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_all_categories(self) -> List[Category]:
        """Todas as categorias (admin)"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Category).order_by(Category.position, Category.name)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_by_name(self, name: str) -> Optional[Category]:
        """Busca categoria pelo nome"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Category).where(Category.name == name)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_or_create(
        self,
        name: str,
        emoji: str = "📦",
    ) -> Category:
        """Busca ou cria categoria"""
        category = await self.get_by_name(name)
        
        if category:
            return category
        
        db = await get_db()
        try:
            category = Category(
                name=name,
                emoji=emoji,
            )
            db.add(category)
            await db.commit()
            await db.refresh(category)
            
            logger.info(f"Categoria criada: {name}")
            
            return category
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def update_category(
        self,
        category_id: int,
        **kwargs,
    ) -> Optional[Category]:
        """Atualiza categoria"""
        return await self.update(category_id, **kwargs)
    
    async def get_product_count(self, category_id: int) -> int:
        """Número de produtos na categoria"""
        db = await get_db()
        try:
            from database.models.product import Product
            
            result = await db.execute(
                select(func.count(Product.id))
                .where(
                    and_(
                        Product.category_id == category_id,
                        Product.is_active == True,
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def toggle_category(self, category_id: int) -> Optional[Category]:
        """Ativa/desativa categoria"""
        category = await self.get_by_id(category_id)
        if not category:
            return None
        
        return await self.update(category_id, is_active=not category.is_active)
    
    async def reorder_categories(
        self,
        category_order: List[dict],
    ) -> bool:
        """Reordena categorias"""
        db = await get_db()
        try:
            for item in category_order:
                await db.execute(
                    __import__('sqlalchemy').update(Category)
                    .where(Category.id == item["id"])
                    .values(position=item["position"])
                )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            return False
        finally:
            await db.close()
    
    async def get_category_with_products(self, category_id: int) -> Optional[Category]:
        """Categoria com produtos carregados"""
        db = await get_db()
        try:
            from sqlalchemy.orm import joinedload
            
            result = await db.execute(
                select(Category)
                .options(joinedload(Category.products))
                .where(Category.id == category_id)
            )
            return result.unique().scalar_one_or_none()
        finally:
            await db.close()
