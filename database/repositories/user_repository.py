"""
Repositório de Usuários
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repositório para operações com usuários"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Busca usuário pelo Telegram ID"""
        db = await get_db()
        try:
            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_or_create(self, telegram_id: int, **kwargs) -> User:
        """Busca ou cria um usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        
        if not user:
            user = await self.create(
                telegram_id=telegram_id,
                **kwargs
            )
            logger.info(f"Novo usuário criado: {telegram_id}")
        else:
            # Atualiza dados básicos
            update_data = {
                "last_activity": datetime.utcnow(),
            }
            if kwargs.get("username"):
                update_data["username"] = kwargs["username"]
            if kwargs.get("first_name"):
                update_data["first_name"] = kwargs["first_name"]
            
            await self.update(user.id, **update_data)
        
        return user
    
    async def get_user_full_data(self, telegram_id: int) -> Optional[Dict]:
        """Busca dados completos do usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        return user.to_dict() if user else None
    
    async def add_balance(self, telegram_id: int, amount: float) -> Optional[User]:
        """Adiciona saldo ao usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        new_balance = user.balance + amount
        return await self.update(user.id, balance=new_balance)
    
    async def remove_balance(self, telegram_id: int, amount: float) -> Optional[User]:
        """Remove saldo do usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        if user.balance < amount:
            return None  # Saldo insuficiente
        
        new_balance = user.balance - amount
        return await self.update(user.id, balance=new_balance)
    
    async def increment_purchases(self, telegram_id: int, amount: float) -> Optional[User]:
        """Incrementa contador de compras"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        return await self.update(
            user.id,
            total_purchases=user.total_purchases + 1,
            total_spent=user.total_spent + amount,
        )
    
    async def search_users(self, query: str, page: int = 1, per_page: int = 10) -> Dict:
        """Busca usuários por nome ou username"""
        db = await get_db()
        try:
            offset = (page - 1) * per_page
            
            # Busca por ID, username ou nome
            try:
                search_id = int(query)
                filter_condition = User.telegram_id == search_id
            except ValueError:
                filter_condition = or_(
                    User.username.ilike(f"%{query}%"),
                    User.first_name.ilike(f"%{query}%"),
                )
            
            # Conta total
            count_query = select(func.count(User.id)).where(filter_condition)
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Busca paginada
            result = await db.execute(
                select(User)
                .where(filter_condition)
                .order_by(User.id.desc())
                .limit(per_page)
                .offset(offset)
            )
            users = result.scalars().all()
            
            return {
                "users": [user.to_dict() for user in users],
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "page": page,
            }
        finally:
            await db.close()
    
    async def get_total_users(self) -> int:
        """Total de usuários cadastrados"""
        return await self.count()
    
    async def get_active_users_today(self) -> int:
        """Usuários ativos hoje"""
        db = await get_db()
        try:
            today = datetime.utcnow().date()
            result = await db.execute(
                select(func.count(User.id))
                .where(func.date(User.last_activity) == today)
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def block_user(self, telegram_id: int) -> Optional[User]:
        """Bloqueia um usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        return await self.update(user.id, is_blocked=True)
    
    async def unblock_user(self, telegram_id: int) -> Optional[User]:
        """Desbloqueia um usuário"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        return await self.update(user.id, is_blocked=False)
