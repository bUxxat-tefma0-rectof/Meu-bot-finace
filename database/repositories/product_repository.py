"""
Repositório de Produtos
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import joinedload

from database.models.product import Product, ProductMedia
from database.models.category import Category
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository[Product]):
    """Repositório para operações com produtos"""
    
    def __init__(self):
        super().__init__(Product)
    
    async def get_active_products(self) -> List[Product]:
        """Busca produtos ativos"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Product)
                .where(Product.is_active == True)
                .order_by(Product.position, Product.name)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """Busca produtos por categoria"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Product)
                .where(
                    and_(
                        Product.category_id == category_id,
                        Product.is_active == True,
                    )
                )
                .order_by(Product.position, Product.name)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_product_with_media(self, product_id: int) -> Optional[Dict]:
        """Busca produto com mídia"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Product)
                .options(joinedload(Product.media_items))
                .where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                return None
            
            data = product.to_dict()
            data["images"] = [m.file_id for m in product.media_items]
            
            return data
        finally:
            await db.close()
    
    async def update_product_image(self, product_id: int, file_id: str) -> bool:
        """Atualiza imagem principal do produto"""
        db = await get_db()
        try:
            # Remove imagens antigas ou adiciona nova
            existing = await db.execute(
                select(ProductMedia).where(
                    and_(
                        ProductMedia.product_id == product_id,
                        ProductMedia.is_main == True,
                    )
                )
            )
            existing_media = existing.scalar_one_or_none()
            
            if existing_media:
                existing_media.file_id = file_id
            else:
                new_media = ProductMedia(
                    product_id=product_id,
                    file_id=file_id,
                    is_main=True,
                    file_type="photo",
                )
                db.add(new_media)
            
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar imagem: {e}")
            return False
        finally:
            await db.close()
    
    async def increment_views(self, product_id: int) -> None:
        """Incrementa visualizações"""
        db = await get_db()
        try:
            await db.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(total_views=Product.total_views + 1)
            )
            await db.commit()
        finally:
            await db.close()
    
    async def increment_sales(self, product_id: int) -> None:
        """Incrementa vendas e decrementa estoque"""
        db = await get_db()
        try:
            await db.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(
                    total_sales=Product.total_sales + 1,
                    stock_count=Product.stock_count - 1,
                )
            )
            await db.commit()
        finally:
            await db.close()
    
    async def get_total_stock(self) -> int:
        """Total de itens em estoque"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(Product.stock_count))
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_sold_out_products(self) -> List[Product]:
        """Produtos esgotados"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Product).where(Product.stock_count == 0)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def toggle_product_status(self, product_id: int) -> Optional[Product]:
        """Ativa/desativa produto"""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        return await self.update(product_id, is_active=not product.is_active)
