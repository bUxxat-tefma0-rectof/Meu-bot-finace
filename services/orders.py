"""
Serviço de Pedidos/Compras
Gerencia o fluxo completo de compra
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.repositories.order_repository import OrderRepository
from database.repositories.product_repository import ProductRepository
from database.repositories.user_repository import UserRepository
from database.repositories.inventory_repository import InventoryRepository

logger = logging.getLogger(__name__)


class OrderService:
    """
    Serviço para processamento de compras
    
    Fluxo:
    1. Verifica saldo
    2. Verifica estoque
    3. Reserva item
    4. Debita saldo
    5. Baixa estoque
    6. Registra pedido
    7. Entrega item
    """
    
    def __init__(self):
        self.order_repo = OrderRepository()
        self.product_repo = ProductRepository()
        self.user_repo = UserRepository()
        self.inventory_repo = InventoryRepository()
    
    async def process_purchase(
        self,
        telegram_id: int,
        product_id: int,
    ) -> Dict[str, Any]:
        """
        Processa uma compra completa
        
        Args:
            telegram_id: ID do comprador
            product_id: ID do produto
            
        Returns:
            Resultado da compra
        """
        try:
            # 1. Busca produto
            product = await self.product_repo.get_by_id(product_id)
            if not product:
                return {"success": False, "error": "Produto não encontrado"}
            
            if not product.is_active:
                return {"success": False, "error": "Produto indisponível"}
            
            # 2. Verifica estoque
            if product.stock_count <= 0:
                return {"success": False, "error": "Produto esgotado"}
            
            # 3. Busca usuário
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if not user:
                return {"success": False, "error": "Usuário não encontrado"}
            
            if user.is_blocked:
                return {"success": False, "error": "Usuário bloqueado"}
            
            # 4. Verifica saldo
            if user.balance < product.price:
                return {
                    "success": False,
                    "error": "Saldo insuficiente",
                    "error_type": "insufficient_balance",
                    "balance": user.balance,
                    "price": product.price,
                }
            
            # 5. Reserva item do estoque
            stock_item = await self.inventory_repo.reserve_item(product_id)
            
            if not stock_item:
                return {"success": False, "error": "Erro ao reservar item. Tente novamente."}
            
            # 6. Prepara conteúdo de entrega
            if product.delivery_type == 1:
                # Texto único com código
                delivery_content = product.delivery_text.replace(
                    "{codigo}", stock_item.code
                ) if product.delivery_text else stock_item.code
            else:
                # Código individual
                delivery_content = stock_item.code
            
            # 7. Debita saldo
            user = await self.user_repo.remove_balance(telegram_id, product.price)
            if not user:
                # Rollback: devolve item ao estoque
                await self.inventory_repo.release_item(stock_item.id)
                return {"success": False, "error": "Erro ao processar pagamento"}
            
            # 8. Cria pedido
            order = await self.order_repo.create_order(
                user_id=user.id,
                product_data={
                    "product_id": product.id,
                    "name": product.name,
                    "price": product.price,
                },
                stock_item_code=delivery_content,
            )
            
            # 9. Marca item como vendido
            await self.inventory_repo.mark_as_sold(
                stock_item.id,
                order.id,
                telegram_id,
            )
            
            # 10. Atualiza estatísticas do produto
            await self.product_repo.increment_sales(product_id)
            
            # 11. Atualiza usuário
            await self.user_repo.increment_purchases(telegram_id, product.price)
            
            logger.info(
                f"Compra realizada: user={telegram_id}, "
                f"product={product.name}, price={product.price}"
            )
            
            return {
                "success": True,
                "purchase": {
                    "order_id": order.id,
                    "product_name": product.name,
                    "price": product.price,
                    "delivery_content": delivery_content,
                    "warranty": product.warranty,
                    "purchase_date": order.created_at.strftime("%d/%m/%Y"),
                    "purchase_time": order.created_at.strftime("%H:%M"),
                },
                "new_balance": user.balance,
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar compra: {e}")
            return {"success": False, "error": "Erro interno. Tente novamente."}
    
    async def get_user_orders(
        self,
        telegram_id: int,
        page: int = 1,
        per_page: int = 5,
    ) -> Dict[str, Any]:
        """
        Histórico de compras do usuário
        
        Args:
            telegram_id: ID do usuário
            page: Página
            per_page: Itens por página
            
        Returns:
            Pedidos paginados
        """
        return await self.order_repo.get_user_orders(telegram_id, page, per_page)
    
    async def get_order_detail(self, order_id: int) -> Optional[Dict]:
        """Detalhes de um pedido"""
        order = await self.order_repo.get_order_with_items(order_id)
        
        if not order:
            return None
        
        order_data = order.to_dict()
        
        if order.items:
            item = order.items[0]
            order_data.update({
                "product_name": item.product_name,
                "price": item.price,
                "delivery_content": item.delivery_content,
                "warranty": item.product.warranty if item.product else "N/A",
                "payment_method": order.payment_method,
            })
        
        return order_data
    
    async def get_sales_count_today(self) -> int:
        """Vendas de hoje"""
        return await self.order_repo.get_sales_count_today()
    
    async def get_total_sales_count(self) -> int:
        """Total de vendas"""
        return await self.order_repo.get_total_sales_count()
    
    async def get_revenue_today(self) -> float:
        """Faturamento de hoje"""
        return await self.order_repo.get_revenue_today()
    
    async def get_total_revenue(self) -> float:
        """Faturamento total"""
        return await self.order_repo.get_total_revenue()
