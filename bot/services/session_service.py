"""
Serviço de Sessão
Gerencia estado da conversa e dados temporários
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.connection import get_db
from database.models.user_session import UserSession
from database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SessionService:
    """
    Serviço de gerenciamento de sessão do usuário
    
    Responsável por:
    - Salvar estado atual da conversa
    - Recuperar estado após reinício
    - Armazenar dados temporários
    - Gerenciar IDs de mensagens para limpeza
    """
    
    def __init__(self):
        self._local_cache: Dict[int, Dict[str, Any]] = {}
    
    async def save_session(
        self,
        telegram_id: int,
        current_state: str = None,
        current_menu: str = None,
        temp_data: Dict = None,
        message_ids: List[int] = None,
    ):
        """
        Salva sessão do usuário
        
        Args:
            telegram_id: ID do usuário
            current_state: Estado atual
            current_menu: Menu atual
            temp_data: Dados temporários
            message_ids: IDs de mensagens
        """
        try:
            db = await get_db()
            
            # Busca usuário
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(telegram_id)
            
            if not user:
                return
            
            # Busca sessão existente
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserSession).where(UserSession.user_id == user.id)
            )
            session = result.scalar_one_or_none()
            
            if session:
                # Atualiza
                if current_state:
                    session.current_state = current_state
                if current_menu:
                    session.current_menu = current_menu
                if temp_data:
                    session.temp_data = json.dumps(temp_data)
                if message_ids:
                    session.message_ids = json.dumps(message_ids)
                
                session.last_activity = datetime.utcnow()
                
            else:
                # Cria nova
                session = UserSession(
                    user_id=user.id,
                    current_state=current_state or "",
                    current_menu=current_menu or "",
                    temp_data=json.dumps(temp_data) if temp_data else None,
                    message_ids=json.dumps(message_ids) if message_ids else None,
                )
                db.add(session)
            
            await db.commit()
            
            # Atualiza cache local
            self._local_cache[telegram_id] = {
                "state": current_state,
                "menu": current_menu,
                "data": temp_data or {},
                "messages": message_ids or [],
            }
            
        except Exception as e:
            logger.error(f"Erro ao salvar sessão: {e}")
        finally:
            await db.close()
    
    async def load_session(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Carrega sessão do usuário
        
        Args:
            telegram_id: ID do usuário
            
        Returns:
            Dados da sessão ou None
        """
        # Verifica cache local primeiro
        if telegram_id in self._local_cache:
            return self._local_cache[telegram_id]
        
        try:
            db = await get_db()
            
            from sqlalchemy import select
            
            # Busca usuário
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(telegram_id)
            
            if not user:
                return None
            
            # Busca sessão
            result = await db.execute(
                select(UserSession).where(UserSession.user_id == user.id)
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            # Converte para dicionário
            session_data = {
                "state": session.current_state,
                "menu": session.current_menu,
                "data": json.loads(session.temp_data) if session.temp_data else {},
                "messages": json.loads(session.message_ids) if session.message_ids else [],
            }
            
            # Atualiza cache
            self._local_cache[telegram_id] = session_data
            
            return session_data
            
        except Exception as e:
            logger.error(f"Erro ao carregar sessão: {e}")
            return None
        finally:
            await db.close()
    
    async def clear_session(self, telegram_id: int):
        """
        Limpa sessão do usuário
        
        Args:
            telegram_id: ID do usuário
        """
        # Remove do cache
        self._local_cache.pop(telegram_id, None)
        
        try:
            db = await get_db()
            
            from sqlalchemy import delete
            
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(telegram_id)
            
            if user:
                await db.execute(
                    delete(UserSession).where(UserSession.user_id == user.id)
                )
                await db.commit()
                
        except Exception as e:
            logger.error(f"Erro ao limpar sessão: {e}")
        finally:
            await db.close()
    
    async def update_temp_data(
        self,
        telegram_id: int,
        key: str,
        value: Any,
    ):
        """
        Atualiza dado temporário na sessão
        
        Args:
            telegram_id: ID do usuário
            key: Chave
            value: Valor
        """
        session = await self.load_session(telegram_id)
        
        if not session:
            session = {"state": None, "menu": None, "data": {}, "messages": []}
        
        session["data"][key] = value
        
        await self.save_session(
            telegram_id=telegram_id,
            temp_data=session["data"],
        )
    
    async def get_temp_data(
        self,
        telegram_id: int,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Obtém dado temporário da sessão
        
        Args:
            telegram_id: ID do usuário
            key: Chave
            default: Valor padrão
            
        Returns:
            Valor armazenado
        """
        session = await self.load_session(telegram_id)
        
        if session and key in session.get("data", {}):
            return session["data"][key]
        
        return default
    
    async def add_message_id(
        self,
        telegram_id: int,
        message_id: int,
    ):
        """
        Adiciona ID de mensagem para limpeza
        
        Args:
            telegram_id: ID do usuário
            message_id: ID da mensagem
        """
        session = await self.load_session(telegram_id)
        
        messages = session.get("messages", []) if session else []
        messages.append(message_id)
        
        # Mantém últimos 50 IDs
        if len(messages) > 50:
            messages = messages[-50:]
        
        await self.save_session(
            telegram_id=telegram_id,
            message_ids=messages,
        )


# Instância global
session_service = SessionService()
