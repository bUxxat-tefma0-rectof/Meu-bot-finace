"""
Serviço de Estoque
Gerencia itens de estoque, adição e remoção
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.repositories.inventory_repository import InventoryRepository
from database.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Serviço para operações de estoque
    
    Gerencia:
    - Adição de itens
    - Remoção de itens
    - Reserva para compra
    - Histórico
    """
    
    def __init__(self):
        self.inventory_repo = InventoryRepository()
        self.audit_repo = AuditRepository()
    
    async def add_items(
        self,
        product_id: int,
        items: List[str],
        admin_id: int,
    ) -> Dict[str, Any]:
        """
        Adiciona itens ao estoque
        
        Args:
            product_id: ID do produto
            items: Lista de códigos
            admin_id: ID do admin
            
        Returns:
            Resultado com contagem
        """
        try:
            # Remove duplicatas
            unique_items = list(set(item.strip() for item in items if item.strip()))
            duplicates = len(items) - len(unique_items)
            
            # Adiciona ao banco
            added = 0
            for code in unique_items:
                success = await self.inventory_repo.add_item(
                    product_id=product_id,
                    code=code,
                    added_by=admin_id,
                )
                if success:
                    added += 1
            
            # Atualiza contagem no produto
            from database.repositories.product_repository import ProductRepository
            product_repo = ProductRepository()
            
            product = await product_repo.get_by_id(product_id)
            if product:
                await product_repo.update(
                    product_id,
                    stock_count=product.stock_count + added,
                )
            
            # Auditoria
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="add_stock",
                entity_type="product",
                entity_id=product_id,
                description=f"Adicionados {added} itens ao estoque",
            )
            
            logger.info(f"Estoque adicionado: product={product_id}, items={added}")
            
            return {
                "success": True,
                "items_added": added,
                "duplicates": duplicates,
                "total_stock": product.stock_count + added if product else added,
            }
            
        except Exception as e:
            logger.error(f"Erro ao adicionar estoque: {e}")
            return {"success": False, "error": str(e)}
    
    async def reserve_item(self, product_id: int) -> Optional[Dict]:
        """
        Reserva um item do estoque para compra
        
        Args:
            product_id: ID do produto
            
        Returns:
            Item reservado ou None
        """
        item = await self.inventory_repo.reserve_item(product_id)
        
        if item:
            return item.to_dict()
        
        return None
    
    async def mark_as_sold(
        self,
        item_id: int,
        order_id: int,
        user_id: int,
    ) -> bool:
        """
        Marca item como vendido
        
        Args:
            item_id: ID do item
            order_id: ID do pedido
            user_id: ID do comprador
            
        Returns:
            Sucesso
        """
        return await self.inventory_repo.mark_as_sold(item_id, order_id, user_id)
    
    async def get_available_items(self, product_id: int) -> List[Dict]:
        """Itens disponíveis de um produto"""
        items = await self.inventory_repo.get_available_items(product_id)
        return [item.to_dict() for item in items]
    
    async def get_sold_items(self, product_id: int = None) -> List[Dict]:
        """Itens vendidos"""
        items = await self.inventory_repo.get_sold_items(product_id)
        return [item.to_dict() for item in items]
    
    async def remove_item(self, item_id: int, admin_id: int) -> Dict[str, Any]:
        """Remove um item específico"""
        success = await self.inventory_repo.delete(item_id)
        
        if success:
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="remove_stock",
                entity_type="stock_item",
                entity_id=item_id,
                description=f"Item removido do estoque",
            )
            return {"success": True}
        
        return {"success": False, "error": "Item não encontrado"}
    
    async def get_stock_history(self, limit: int = 50) -> List[Dict]:
        """Histórico de movimentações"""
        logs = await self.audit_repo.get_logs(
            entity_type="stock_item",
            limit=limit,
        )
        return [log.to_dict() for log in logs]
    
    async def get_item_by_code(self, product_id: int, code: str) -> Optional[Dict]:
        """Busca item por código"""
        item = await self.inventory_repo.get_item_by_code(product_id, code)
        return item.to_dict() if item else None
    
    async def get_stock_count(self, product_id: int) -> int:
        """Contagem de itens disponíveis"""
        return await self.inventory_repo.get_available_count(product_id)
