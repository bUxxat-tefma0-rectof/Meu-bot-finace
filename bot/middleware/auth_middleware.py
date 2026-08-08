"""
Middleware de Autenticação e Autorização
Verifica canal obrigatório, bloqueios e registra atividade
"""

import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, Application
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Middleware que executa antes de cada handler
    
    Responsável por:
    - Verificar inscrição no canal obrigatório
    - Verificar se usuário está bloqueado
    - Registrar atividade do usuário
    - Bloquear acesso não autorizado
    """
    
    def __init__(self):
        self._subscription_cache: Dict[int, tuple] = {}
        # {user_id: (is_subscribed, timestamp)}
    
    async def check_channel_subscription(
        self,
        user_id: int,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:
        """
        Verifica se usuário está inscrito no canal obrigatório
        
        Args:
            user_id: ID do usuário
            context: Contexto do bot
            
        Returns:
            Está inscrito
        """
        # Verifica cache (válido por 5 minutos)
        if user_id in self._subscription_cache:
            is_subscribed, cache_time = self._subscription_cache[user_id]
            if (datetime.utcnow() - cache_time).total_seconds() < 300:
                return is_subscribed
        
        try:
            channel_id = settings.REQUIRED_CHANNEL_ID
            
            if not channel_id:
                # Canal não configurado - libera acesso
                return True
            
            # Converte ID se necessário
            if channel_id.startswith("-100"):
                chat_id = int(channel_id)
            elif channel_id.startswith("@"):
                chat_id = channel_id
            else:
                try:
                    chat_id = int(channel_id)
                except ValueError:
                    chat_id = channel_id
            
            # Consulta API do Telegram
            member = await context.bot.get_chat_member(
                chat_id=chat_id,
                user_id=user_id,
            )
            
            # Status válidos para acesso
            valid_statuses = ["member", "administrator", "creator"]
            is_subscribed = member.status in valid_statuses
            
            # Atualiza cache
            self._subscription_cache[user_id] = (is_subscribed, datetime.utcnow())
            
            return is_subscribed
            
        except TelegramError as e:
            logger.error(f"Erro ao verificar canal: {e}")
            # Se der erro, libera acesso para não travar usuários
            return True
    
    async def check_user_blocked(self, telegram_id: int) -> bool:
        """
        Verifica se usuário está bloqueado
        
        Args:
            telegram_id: ID do usuário
            
        Returns:
            Está bloqueado
        """
        try:
            from database.repositories.user_repository import UserRepository
            repo = UserRepository()
            
            user = await repo.get_by_telegram_id(telegram_id)
            
            if user and user.is_blocked:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar bloqueio: {e}")
            return False
    
    async def track_activity(self, telegram_id: int):
        """
        Registra atividade do usuário
        
        Args:
            telegram_id: ID do usuário
        """
        try:
            from database.repositories.user_repository import UserRepository
            repo = UserRepository()
            
            user = await repo.get_by_telegram_id(telegram_id)
            
            if user:
                await repo.update(user.id, last_activity=datetime.utcnow())
                
        except Exception as e:
            logger.debug(f"Erro ao registrar atividade: {e}")


# Instância global do middleware
auth_middleware = AuthMiddleware()


async def check_channel_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[bool]:
    """
    Decorator/ função para verificar canal
    
    Args:
        update: Update do Telegram
        context: Contexto
        
    Returns:
        True se inscrito, False se bloqueado, None se erro
    """
    if not update.effective_user:
        return None
    
    user_id = update.effective_user.id
    
    # Não verifica para admins
    if settings.is_admin(user_id):
        return True
    
    return await auth_middleware.check_channel_subscription(user_id, context)


async def check_user_blocked(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Verifica se usuário está bloqueado
    
    Args:
        update: Update
        context: Contexto
        
    Returns:
        Está bloqueado
    """
    if not update.effective_user:
        return False
    
    user_id = update.effective_user.id
    
    # Admins nunca são bloqueados
    if settings.is_admin(user_id):
        return False
    
    return await auth_middleware.check_user_blocked(user_id)


async def track_user_activity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Registra atividade do usuário
    
    Args:
        update: Update
        context: Contexto
    """
    if update.effective_user:
        await auth_middleware.track_activity(update.effective_user.id)
