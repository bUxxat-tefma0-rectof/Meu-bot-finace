"""
Serviço de Produtos
Gerencia categorias, produtos e estatísticas
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from database.repositories.product_repository import ProductRepository
from database.repositories.audit_repository import AuditRepository
from database.models.category import Category

logger = logging.getLogger(__name__)


class ProductService:
    """
    Serviço para operações com produtos e categorias
    """
    
    def __init__(self):
        self.product_repo = ProductRepository()
        self.audit_repo = AuditRepository()
        
        # Cache de visualizadores ativos
        self._active_viewers = {}  # {product_id: {user_id: timestamp}}
    
    # ===========================================
    # CATEGORIAS
    # ===========================================
    
    async def get_active_categories(self) -> List[Dict]:
        """Busca categorias ativas ordenadas"""
        categories = await self.product_repo.get_active_categories()
        return [cat.to_dict() for cat in categories]
    
    async def get_category(self, category_id: int) -> Optional[Dict]:
        """Busca categoria por ID"""
        category = await self.product_repo.get_category(category_id)
        return category.to_dict() if category else None
    
    async def get_all_categories(self) -> List[Dict]:
        """Busca todas as categorias (admin)"""
        categories = await self.product_repo.get_all_categories()
        return [cat.to_dict() for cat in categories]
    
    async def create_category(
        self,
        name: str,
        emoji: str = "📦",
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Cria nova categoria"""
        try:
            category = await self.product_repo.create_category(
                name=name,
                emoji=emoji,
            )
            
            if admin_id:
                await self.audit_repo.create_log(
                    admin_id=admin_id,
                    action="create",
                    entity_type="category",
                    entity_id=category.id,
                    description=f"Categoria criada: {name}",
                )
            
            return {"success": True, "category": category.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_category(
        self,
        category_id: int,
        admin_id: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Atualiza categoria"""
        category = await self.product_repo.update_category(category_id, **kwargs)
        
        if not category:
            return {"success": False, "error": "Categoria não encontrada"}
        
        await self.audit_repo.create_log(
            admin_id=admin_id,
            action="update",
            entity_type="category",
            entity_id=category_id,
            description=f"Categoria atualizada: {kwargs}",
        )
        
        return {"success": True, "category": category.to_dict()}
    
    # ===========================================
    # PRODUTOS
    # ===========================================
    
    async def get_product(self, product_id: int) -> Optional[Dict]:
        """Busca produto por ID"""
        product = await self.product_repo.get_product_with_media(product_id)
        return product
    
    async def get_products_by_category(self, category_id: int) -> List[Dict]:
        """Busca produtos de uma categoria"""
        products = await self.product_repo.get_products_by_category(category_id)
        return [p.to_dict() for p in products]
    
    async def get_all_products_admin(self) -> List[Dict]:
        """Busca todos os produtos (admin)"""
        products = await self.product_repo.get_all_products()
        return [p.to_dict() for p in products]
    
    async def get_active_products(self) -> List[Dict]:
        """Busca produtos ativos"""
        products = await self.product_repo.get_active_products()
        return [p.to_dict() for p in products]
    
    async def create_product(
        self,
        product_data: Dict[str, Any],
        admin_id: int,
    ) -> Dict[str, Any]:
        """
        Cria novo produto
        
        Args:
            product_data: Dados do produto
            admin_id: ID do admin
            
        Returns:
            Resultado com ID do produto criado
        """
        try:
            # Busca ou cria categoria
            category_name = product_data.get("category", "Geral")
            category = await self.product_repo.get_or_create_category(category_name)
            
            product = await self.product_repo.create(
                name=product_data.get("name"),
                category_id=category.id,
                price=product_data.get("price", 0),
                description=product_data.get("description", ""),
                warranty=product_data.get("warranty", "7 dias"),
                delivery_text=product_data.get("delivery_text", ""),
                delivery_type=product_data.get("delivery_type", 1),
                created_by=admin_id,
            )
            
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="create",
                entity_type="product",
                entity_id=product.id,
                description=f"Produto criado: {product.name}",
            )
            
            return {"success": True, "product_id": product.id}
        except Exception as e:
            logger.error(f"Erro ao criar produto: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_product_field(
        self,
        product_id: int,
        field: str,
        value: Any,
        admin_id: int,
    ) -> Dict[str, Any]:
        """Atualiza campo específico do produto"""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return {"success": False, "error": "Produto não encontrado"}
        
        old_value = getattr(product, field, None)
        
        update_data = {field: value}
        updated = await self.product_repo.update(product_id, **update_data)
        
        if not updated:
            return {"success": False, "error": "Erro ao atualizar"}
        
        await self.audit_repo.create_log(
            admin_id=admin_id,
            action="update",
            entity_type="product",
            entity_id=product_id,
            description=f"Campo '{field}' alterado",
            old_value=str(old_value),
            new_value=str(value),
        )
        
        return {"success": True}
    
    async def update_product_image(
        self,
        product_id: int,
        file_id: str,
        admin_id: int,
    ) -> Dict[str, Any]:
        """Atualiza imagem do produto"""
        success = await self.product_repo.update_product_image(product_id, file_id)
        
        if success:
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="update",
                entity_type="product",
                entity_id=product_id,
                description="Imagem do produto atualizada",
            )
            return {"success": True}
        
        return {"success": False, "error": "Erro ao atualizar imagem"}
    
    async def toggle_product(
        self,
        product_id: int,
        admin_id: int,
    ) -> Dict[str, Any]:
        """Ativa/desativa produto"""
        product = await self.product_repo.toggle_product_status(product_id)
        
        if not product:
            return {"success": False, "error": "Produto não encontrado"}
        
        await self.audit_repo.create_log(
            admin_id=admin_id,
            action="toggle",
            entity_type="product",
            entity_id=product_id,
            description=f"Produto {'ativado' if product.is_active else 'desativado'}",
        )
        
        return {
            "success": True,
            "status": "ativado" if product.is_active else "desativado",
        }
    
    async def delete_product(
        self,
        product_id: int,
        admin_id: int,
    ) -> Dict[str, Any]:
        """Exclui produto"""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return {"success": False, "error": "Produto não encontrado"}
        
        deleted = await self.product_repo.delete(product_id)
        
        if deleted:
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="delete",
                entity_type="product",
                entity_id=product_id,
                description=f"Produto excluído: {product.name}",
            )
            return {"success": True}
        
        return {"success": False, "error": "Erro ao excluir"}
    
    # ===========================================
    # ESTATÍSTICAS
    # ===========================================
    
    async def increment_views(self, product_id: int, user_id: int):
        """
        Registra visualização do produto
        
        Mantém cache de visualizadores ativos
        """
        await self.product_repo.increment_views(product_id)
        
        # Atualiza cache de visualizadores
        if product_id not in self._active_viewers:
            self._active_viewers[product_id] = {}
        
        self._active_viewers[product_id][user_id] = datetime.utcnow()
    
    async def get_active_viewers(self, product_id: int, window_seconds: int = 300) -> int:
        """
        Retorna número de visualizadores ativos
        
        Args:
            product_id: ID do produto
            window_seconds: Janela de tempo para considerar ativo
            
        Returns:
            Número de visualizadores
        """
        if product_id not in self._active_viewers:
            return 0
        
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Remove visualizadores inativos
        active = {
            uid: ts
            for uid, ts in self._active_viewers[product_id].items()
            if ts > cutoff
        }
        
        self._active_viewers[product_id] = active
        
        return len(active)
    
    async def get_total_stock(self) -> int:
        """Total de itens em estoque"""
        return await self.product_repo.get_total_stock()
    
    async def get_total_sold(self) -> int:
        """Total de produtos vendidos"""
        return await self.product_repo.get_total_sold()
    
    async def get_sold_out_count(self) -> int:
        """Número de produtos esgotados"""
        products = await self.product_repo.get_sold_out_products()
        return len(products)
    
    async def update_statistics(self, context=None):
        """Atualiza estatísticas (job)"""
        # Limpa cache de visualizadores antigos
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        
        for product_id in list(self._active_viewers.keys()):
            self._active_viewers[product_id] = {
                uid: ts
                for uid, ts in self._active_viewers[product_id].items()
                if ts > cutoff
            }
            
            if not self._active_viewers[product_id]:
                del self._active_viewers[product_id]
