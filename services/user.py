"""
Serviço de Usuários
Gerencia cadastro, consulta, saldo e bloqueio de usuários
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.repositories.user_repository import UserRepository
from database.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class UserService:
    """
    Serviço para operações com usuários
    
    Atua como camada intermediária entre os handlers
    e o repositório, aplicando regras de negócio.
    """
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.audit_repo = AuditRepository()
    
    async def register_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        referrer_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Registra ou atualiza um usuário
        
        Args:
            telegram_id: ID do Telegram
            username: Nome de usuário
            first_name: Primeiro nome
            last_name: Sobrenome
            referrer_id: ID de quem indicou (afiliado)
            
        Returns:
            Dados do usuário
        """
        try:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            is_new = False
            
            if not user:
                # Novo usuário
                user = await self.user_repo.create(
                    telegram_id=telegram_id,
                    username=username or "",
                    first_name=first_name or "",
                    last_name=last_name or "",
                    referrer_id=referrer_id,
                )
                is_new = True
                
                # Registra afiliado se houver referrer
                if referrer_id and referrer_id != telegram_id:
                    await self._register_affiliate(referrer_id, telegram_id)
                
                logger.info(f"Novo usuário registrado: {telegram_id}")
            else:
                # Atualiza dados
                update_data = {"last_activity": datetime.utcnow()}
                if username:
                    update_data["username"] = username
                if first_name:
                    update_data["first_name"] = first_name
                if last_name:
                    update_data["last_name"] = last_name
                
                await self.user_repo.update(user.id, **update_data)
            
            user_data = user.to_dict()
            user_data["is_new"] = is_new
            
            return user_data
            
        except Exception as e:
            logger.error(f"Erro ao registrar usuário: {e}")
            return {"telegram_id": telegram_id, "balance": 0, "total_purchases": 0, "is_new": False}
    
    async def get_user(self, telegram_id: int) -> Dict[str, Any]:
        """
        Busca dados básicos do usuário
        
        Args:
            telegram_id: ID do Telegram
            
        Returns:
            Dict com dados do usuário
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        
        if not user:
            return {
                "telegram_id": telegram_id,
                "balance": 0,
                "total_purchases": 0,
                "total_spent": 0,
                "first_name": "Usuário",
                "username": "",
            }
        
        return user.to_dict()
    
    async def get_user_full_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca dados completos do usuário
        
        Args:
            telegram_id: ID do Telegram
            
        Returns:
            Dict com todos os dados ou None
        """
        return await self.user_repo.get_user_full_data(telegram_id)
    
    async def add_balance(
        self,
        telegram_id: int,
        amount: float,
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Adiciona saldo ao usuário
        
        Args:
            telegram_id: ID do usuário
            amount: Valor a adicionar
            admin_id: ID do admin (se for adição manual)
            
        Returns:
            Resultado da operação
        """
        if amount <= 0:
            return {"success": False, "error": "Valor deve ser positivo"}
        
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        old_balance = user.balance
        updated_user = await self.user_repo.add_balance(telegram_id, amount)
        
        if not updated_user:
            return {"success": False, "error": "Erro ao adicionar saldo"}
        
        # Registra auditoria
        if admin_id:
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="add_balance",
                entity_type="user",
                entity_id=user.id,
                description=f"Adição manual de saldo: R$ {amount:.2f}",
                old_value=str(old_balance),
                new_value=str(updated_user.balance),
            )
        
        logger.info(f"Saldo adicionado: user={telegram_id}, amount={amount}")
        
        return {
            "success": True,
            "new_balance": updated_user.balance,
            "old_balance": old_balance,
            "amount": amount,
        }
    
    async def remove_balance(
        self,
        telegram_id: int,
        amount: float,
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Remove saldo do usuário
        
        Args:
            telegram_id: ID do usuário
            amount: Valor a remover
            admin_id: ID do admin
            
        Returns:
            Resultado da operação
        """
        if amount <= 0:
            return {"success": False, "error": "Valor deve ser positivo"}
        
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        if user.balance < amount:
            return {"success": False, "error": "Saldo insuficiente"}
        
        old_balance = user.balance
        updated_user = await self.user_repo.remove_balance(telegram_id, amount)
        
        if not updated_user:
            return {"success": False, "error": "Erro ao remover saldo"}
        
        # Registra auditoria
        if admin_id:
            await self.audit_repo.create_log(
                admin_id=admin_id,
                action="remove_balance",
                entity_type="user",
                entity_id=user.id,
                description=f"Remoção manual de saldo: R$ {amount:.2f}",
                old_value=str(old_balance),
                new_value=str(updated_user.balance),
            )
        
        return {
            "success": True,
            "new_balance": updated_user.balance,
            "old_balance": old_balance,
            "amount": amount,
        }
    
    async def deduct_balance(
        self,
        telegram_id: int,
        amount: float,
    ) -> Dict[str, Any]:
        """
        Deduz saldo para compra
        
        Args:
            telegram_id: ID do usuário
            amount: Valor da compra
            
        Returns:
            Resultado
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        if user.balance < amount:
            return {
                "success": False,
                "error": "Saldo insuficiente",
                "error_type": "insufficient_balance",
                "balance": user.balance,
                "needed": amount,
            }
        
        updated_user = await self.user_repo.remove_balance(telegram_id, amount)
        
        if not updated_user:
            return {"success": False, "error": "Erro ao processar pagamento"}
        
        # Incrementa contador de compras
        await self.user_repo.increment_purchases(telegram_id, amount)
        
        return {
            "success": True,
            "new_balance": updated_user.balance,
            "amount": amount,
        }
    
    async def get_total_users(self) -> int:
        """Total de usuários"""
        return await self.user_repo.get_total_users()
    
    async def get_active_users_today(self) -> int:
        """Usuários ativos hoje"""
        return await self.user_repo.get_active_users_today()
    
    async def get_all_users(self, page: int = 1, per_page: int = 10) -> Dict:
        """Lista todos os usuários (admin)"""
        return await self.user_repo.get_all_users(page, per_page)
    
    async def search_users(self, query: str, page: int = 1, per_page: int = 10) -> Dict:
        """Busca usuários"""
        return await self.user_repo.search_users(query, page, per_page)
    
    async def block_user(self, telegram_id: int, admin_id: int) -> Dict[str, Any]:
        """Bloqueia usuário"""
        user = await self.user_repo.block_user(telegram_id)
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        await self.audit_repo.create_log(
            admin_id=admin_id,
            action="block",
            entity_type="user",
            entity_id=user.id,
            description=f"Usuário bloqueado: {telegram_id}",
        )
        
        return {"success": True}
    
    async def unblock_user(self, telegram_id: int, admin_id: int) -> Dict[str, Any]:
        """Desbloqueia usuário"""
        user = await self.user_repo.unblock_user(telegram_id)
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        await self.audit_repo.create_log(
            admin_id=admin_id,
            action="unblock",
            entity_type="user",
            entity_id=user.id,
            description=f"Usuário desbloqueado: {telegram_id}",
        )
        
        return {"success": True}
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Busca usuário por username"""
        user = await self.user_repo.get_by_username(username)
        return user.to_dict() if user else None
    
    async def _register_affiliate(self, referrer_id: int, referred_id: int):
        """Registra relação de afiliado"""
        try:
            from database.repositories.affiliate_repository import AffiliateRepository
            affiliate_repo = AffiliateRepository()
            
            await affiliate_repo.create_affiliate(
                referrer_id=referrer_id,
                referred_id=referred_id,
            )
            
            # Atualiza contador de indicados
            referrer = await self.user_repo.get_by_telegram_id(referrer_id)
            if referrer:
                await self.user_repo.update(
                    referrer.id,
                    total_referrals=referrer.total_referrals + 1,
                )
            
            logger.info(f"Afiliado registrado: {referrer_id} -> {referred_id}")
        except Exception as e:
            logger.error(f"Erro ao registrar afiliado: {e}")
