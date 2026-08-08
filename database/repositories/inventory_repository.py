"""
Repositório de Estoque
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, func, and_

from database.models.stock_item import StockItem
from database.models.product import Product
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class InventoryRepository(BaseRepository[StockItem]):
    """Repositório para operações de estoque"""
    
    def __init__(self):
        super().__init__(StockItem)
    
    async def add_item(
        self,
        product_id: int,
        code: str,
        added_by: int = None,
    ) -> bool:
        """Adiciona um item ao estoque"""
        db = await get_db()
        try:
            # Verifica se código já existe para este produto
            existing = await db.execute(
                select(StockItem)
                .where(
                    and_(
                        StockItem.product_id == product_id,
                        StockItem.code == code,
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                return False  # Item duplicado
            
            item = StockItem(
                product_id=product_id,
                code=code,
                status="available",
                added_by=added_by,
            )
            db.add(item)
            await db.commit()
            
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao adicionar item: {e}")
            return False
        finally:
            await db.close()
    
    async def reserve_item(self, product_id: int) -> Optional[StockItem]:
        """Reserva um item disponível"""
        db = await get_db()
        try:
            # Busca primeiro item disponível
            result = await db.execute(
                select(StockItem)
                .where(
                    and_(
                        StockItem.product_id == product_id,
                        StockItem.status == "available",
                    )
                )
                .limit(1)
            )
            item = result.scalar_one_or_none()
            
            if item:
                # Marca como reservado
                item.status = "reserved"
                item.updated_at = datetime.utcnow()
                await db.commit()
            
            return item
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao reservar item: {e}")
            return None
        finally:
            await db.close()
    
    async def mark_as_sold(
        self,
        item_id: int,
        order_id: int,
        user_id: int,
    ) -> bool:
        """Marca item como vendido"""
        db = await get_db()
        try:
            await db.execute(
                update(StockItem)
                .where(StockItem.id == item_id)
                .values(
                    status="sold",
                    order_id=order_id,
                    sold_to=user_id,
                    sold_at=datetime.utcnow(),
                )
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            return False
        finally:
            await db.close()
    
    async def release_item(self, item_id: int) -> bool:
        """Libera item reservado de volta"""
        db = await get_db()
        try:
            await db.execute(
                update(StockItem)
                .where(StockItem.id == item_id)
                .values(status="available")
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            return False
        finally:
            await db.close()
    
    async def get_available_items(self, product_id: int) -> List[StockItem]:
        """Itens disponíveis de um produto"""
        db = await get_db()
        try:
            result = await db.execute(
                select(StockItem)
                .where(
                    and_(
                        StockItem.product_id == product_id,
                        StockItem.status == "available",
                    )
                )
                .order_by(StockItem.id)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_sold_items(
        self,
        product_id: int = None,
    ) -> List[StockItem]:
        """Itens vendidos"""
        db = await get_db()
        try:
            query = select(StockItem).where(StockItem.status == "sold")
            
            if product_id:
                query = query.where(StockItem.product_id == product_id)
            
            result = await db.execute(query.order_by(StockItem.sold_at.desc()))
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_available_count(self, product_id: int) -> int:
        """Contagem de itens disponíveis"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.count(StockItem.id))
                .where(
                    and_(
                        StockItem.product_id == product_id,
                        StockItem.status == "available",
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_item_by_code(
        self,
        product_id: int,
        code: str,
    ) -> Optional[StockItem]:
        """Busca item por código"""
        db = await get_db()
        try:
            result = await db.execute(
                select(StockItem)
                .where(
                    and_(
                        StockItem.product_id == product_id,
                        StockItem.code == code,
                    )
                )
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_items_sold_to_user(self, user_id: int) -> List[StockItem]:
        """Itens comprados por um usuário"""
        db = await get_db()
        try:
            result = await db.execute(
                select(StockItem)
                .where(StockItem.sold_to == user_id)
                .order_by(StockItem.sold_at.desc())
            )
            return result.scalars().all()
        finally:
            await db.close()
