"""
Serviço de Limpeza
Gerencia limpeza de mensagens temporárias e dados antigos
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Serviço para limpeza automática
    
    Responsável por:
    - Limpar mensagens temporárias
    - Remover sessões expiradas
    - Limpar cache de visualizadores
    - Manter o bot organizado
    """
    
    def __init__(self):
        # Registro de mensagens para limpeza
        # {chat_id: [(message_id, timestamp), ...]}
        self._temp_messages: Dict[int, List[Dict]] = {}
    
    def register_message(
        self,
        chat_id: int,
        message_id: int,
        ttl: Optional[int] = None,
    ):
        """
        Registra mensagem para limpeza futura
        
        Args:
            chat_id: ID do chat
            message_id: ID da mensagem
            ttl: Tempo de vida em segundos (padrão: TEMP_MESSAGE_TTL)
        """
        if ttl is None:
            ttl = settings.TEMP_MESSAGE_TTL
        
        if chat_id not in self._temp_messages:
            self._temp_messages[chat_id] = []
        
        self._temp_messages[chat_id].append({
            "message_id": message_id,
            "timestamp": datetime.utcnow(),
            "ttl": ttl,
        })
    
    def register_messages(
        self,
        chat_id: int,
        message_ids: List[int],
        ttl: Optional[int] = None,
    ):
        """
        Registra múltiplas mensagens
        
        Args:
            chat_id: ID do chat
            message_ids: Lista de IDs
            ttl: Tempo de vida
        """
        for msg_id in message_ids:
            self.register_message(chat_id, msg_id, ttl)
    
    async def clean_temp_messages(self, context=None):
        """
        Remove mensagens temporárias expiradas (job)
        
        Args:
            context: Contexto do bot
        """
        if not context or not context.bot:
            return
        
        now = datetime.utcnow()
        total_cleaned = 0
        
        for chat_id in list(self._temp_messages.keys()):
            messages = self._temp_messages[chat_id]
            remaining = []
            
            for msg in messages:
                age = (now - msg["timestamp"]).total_seconds()
                
                if age >= msg["ttl"]:
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=msg["message_id"],
                        )
                        total_cleaned += 1
                    except Exception as e:
                        logger.debug(f"Erro ao deletar mensagem {msg['message_id']}: {e}")
                else:
                    remaining.append(msg)
            
            if remaining:
                self._temp_messages[chat_id] = remaining
            else:
                del self._temp_messages[chat_id]
        
        if total_cleaned > 0:
            logger.info(f"Limpeza: {total_cleaned} mensagens removidas")
    
    async def clean_user_session(
        self,
        chat_id: int,
        context=None,
    ):
        """
        Limpa todas as mensagens de uma sessão
        
        Args:
            chat_id: ID do chat
            context: Contexto do bot
        """
        if chat_id in self._temp_messages:
            messages = self._temp_messages[chat_id]
            
            for msg in messages:
                try:
                    if context and context.bot:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=msg["message_id"],
                        )
                except Exception:
                    pass
            
            del self._temp_messages[chat_id]
    
    async def clean_old_sessions(self, context=None):
        """
        Remove sessões antigas do banco (job)
        
        Args:
            context: Contexto do bot
        """
        try:
            from database.repositories.session_repository import SessionRepository
            repo = SessionRepository()
            
            cutoff = datetime.utcnow() - timedelta(days=7)
            deleted = await repo.delete_old_sessions(cutoff)
            
            if deleted > 0:
                logger.info(f"Limpeza: {deleted} sessões antigas removidas")
        except Exception as e:
            logger.error(f"Erro ao limpar sessões: {e}")
    
    async def clean_old_logs(self, context=None):
        """
        Remove logs antigos (job)
        
        Args:
            context: Contexto do bot
        """
        try:
            from database.repositories.audit_repository import AuditRepository
            repo = AuditRepository()
            
            cutoff = datetime.utcnow() - timedelta(days=30)
            deleted = await repo.delete_old_logs(cutoff)
            
            if deleted > 0:
                logger.info(f"Limpeza: {deleted} logs antigos removidos")
        except Exception as e:
            logger.error(f"Erro ao limpar logs: {e}")
    
    def get_stats(self) -> Dict:
        """
        Estatísticas de mensagens pendentes
        
        Returns:
            Dict com estatísticas
        """
        total_messages = sum(
            len(msgs) for msgs in self._temp_messages.values()
        )
        total_chats = len(self._temp_messages)
        
        return {
            "pending_messages": total_messages,
            "active_chats": total_chats,
        }
