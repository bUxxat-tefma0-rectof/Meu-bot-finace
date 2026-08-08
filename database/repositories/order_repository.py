"""
Repositório de Pedidos
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from database.models.order import Order, OrderItem
from database.models.user import User
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """Repositório para operações com pedidos"""
    
    def __init__(self):
        super().__init__(Order)
    
    async def create_order(self, user_id: int, product_data: Dict, stock_item_code: str) -> Order:
        """Cria um pedido completo"""
        db = await get_db()
        try:
            # Cria o pedido
            order = Order(
                user_id=user_id,
                total_amount=product_data["price"],
                payment_method="balance",
                status="completed",
            )
            db.add(order)
            await db.flush()  # Para obter o ID
            
            # Cria o item do pedido
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_data["product_id"],
                product_name=product_data["name"],
                price=product_data["price"],
                delivery_content=stock_item_code,
            )
            db.add(order_item)
            
            await db.commit()
            await db.refresh(order)
            
            return order
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar pedido: {e}")
            raise
        finally:
            await db.close()
    
    async def get_user_orders(
        self, telegram_id: int, page: int = 1, per_page: int = 5
    ) -> Dict:
        """Busca pedidos de um usuário"""
        db = await get_db()
        try:
            offset = (page - 1) * per_page
            
            # Busca usuário
            user_result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"orders": [], "total": 0, "total_pages": 0, "page": page}
            
            # Conta total
            count_query = select(func.count(Order.id)).where(Order.user_id == user.id)
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Busca pedidos com itens
            result = await db.execute(
                select(Order)
                .options(joinedload(Order.items))
                .where(Order.user_id == user.id)
                .order_by(Order.id.desc())
                .limit(per_page)
                .offset(offset)
            )
            orders = result.unique().scalars().all()
            
            orders_data = []
            for order in orders:
                for item in order.items:
                    orders_data.append({
                        "id": order.id,
                        "product_name": item.product_name,
                        "price": item.price,
                        "delivery_content": item.delivery_content,
                        "purchase_date": order.created_at.strftime("%d/%m/%Y"),
                        "purchase_time": order.created_at.strftime("%H:%M"),
                        "status": order.status,
                        "payment_method": order.payment_method,
                        "warranty": "Ver produto",
                    })
            
            return {
                "orders": orders_data,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "page": page,
            }
        finally:
            await db.close()
    
    async def get_sales_count_today(self) -> int:
        """Vendas de hoje"""
        db = await get_db()
        try:
            today = datetime.utcnow().date()
            result = await db.execute(
                select(func.count(Order.id))
                .where(
                    and_(
                        func.date(Order.created_at) == today,
                        Order.status == "completed",
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_revenue_today(self) -> float:
        """Faturamento de hoje"""
        db = await get_db()
        try:
            today = datetime.utcnow().date()
            result = await db.execute(
                select(func.sum(Order.total_amount))
                .where(
                    and_(
                        func.date(Order.created_at) == today,
                        Order.status == "completed",
                    )
                )
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
    
    async def get_total_revenue(self) -> float:
        """Faturamento total"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(Order.total_amount))
                .where(Order.status == "completed")
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
