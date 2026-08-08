"""
Serviço de Navegação
Controla a navegação entre telas e limpeza de mensagens
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from telegram import Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)


class NavigationService:
    """
    Serviço de navegação do bot
    
    Responsável por:
    - Manter histórico de navegação
    - Editar/substituir mensagens (evitar acúmulo)
    - Limpar mensagens temporárias
    - Gerenciar fluxo de telas
    """
    
    def __init__(self):
        # Histórico de navegação por usuário
        # {user_id: [{"message_id": int, "chat_id": int, "screen": str, "timestamp": datetime}]}
        self._history: Dict[int, List[Dict]] = {}
        
        # Mensagens temporárias para limpeza
        # {user_id: [{"message_id": int, "chat_id": int, "expires_at": datetime}]}
        self._temp_messages: Dict[int, List[Dict]] = {}
    
    def add_to_history(
        self,
        user_id: int,
        message_id: int,
        chat_id: int,
        screen: str,
    ):
        """
        Adiciona mensagem ao histórico de navegação
        
        Args:
            user_id: ID do usuário
            message_id: ID da mensagem
            chat_id: ID do chat
            screen: Nome da tela
        """
        if user_id not in self._history:
            self._history[user_id] = []
        
        self._history[user_id].append({
            "message_id": message_id,
            "chat_id": chat_id,
            "screen": screen,
            "timestamp": datetime.utcnow(),
        })
        
        # Mantém apenas últimas 10 telas
        if len(self._history[user_id]) > 10:
            self._history[user_id] = self._history[user_id][-10:]
    
    def get_last_screen(self, user_id: int) -> Optional[Dict]:
        """
        Retorna última tela do usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dados da última tela ou None
        """
        history = self._history.get(user_id, [])
        
        if history:
            return history[-1]
        
        return None
    
    def get_previous_screen(self, user_id: int) -> Optional[Dict]:
        """
        Retorna tela anterior (para botão voltar)
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dados da tela anterior ou None
        """
        history = self._history.get(user_id, [])
        
        if len(history) >= 2:
            return history[-2]
        
        return None
    
    async def navigate_to(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        screen: str,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML",
        replace_last: bool = True,
    ) -> Optional[Message]:
        """
        Navega para uma nova tela
        
        Args:
            update: Update
            context: Contexto
            screen: Nome da tela
            text: Texto da mensagem
            reply_markup: Teclado inline
            parse_mode: Modo de parse
            replace_last: Substituir última mensagem (evitar acúmulo)
            
        Returns:
            Mensagem enviada
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            if replace_last and update.callback_query:
                # Edita mensagem existente (evita acúmulo)
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True,
                )
                
                message = update.callback_query.message
                
            elif replace_last:
                # Tenta editar última mensagem
                last = self.get_last_screen(user_id)
                
                if last and last["chat_id"] == chat_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=last["message_id"],
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                            disable_web_page_preview=True,
                        )
                        
                        message = None  # Não retorna a mensagem editada
                        
                    except Exception:
                        # Não conseguiu editar - envia nova
                        message = await context.bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                            disable_web_page_preview=True,
                        )
                else:
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                        disable_web_page_preview=True,
                    )
            else:
                # Sempre envia nova mensagem
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True,
                )
            
            # Registra no histórico
            if message:
                self.add_to_history(user_id, message.message_id, chat_id, screen)
            
            return message
            
        except Exception as e:
            logger.error(f"Erro na navegação: {e}")
            
            # Fallback: envia nova mensagem
            try:
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                return message
            except Exception:
                return None
    
    def add_temp_message(
        self,
        user_id: int,
        message_id: int,
        chat_id: int,
        ttl_seconds: int = None,
    ):
        """
        Adiciona mensagem para limpeza automática
        
        Args:
            user_id: ID do usuário
            message_id: ID da mensagem
            chat_id: ID do chat
            ttl_seconds: Tempo de vida em segundos
        """
        if ttl_seconds is None:
            ttl_seconds = settings.TEMP_MESSAGE_TTL
        
        if user_id not in self._temp_messages:
            self._temp_messages[user_id] = []
        
        self._temp_messages[user_id].append({
            "message_id": message_id,
            "chat_id": chat_id,
            "expires_at": datetime.utcnow().timestamp() + ttl_seconds,
        })
    
    async def clean_temp_messages(
        self,
        user_id: int,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        """
        Limpa mensagens temporárias expiradas
        
        Args:
            user_id: ID do usuário
            context: Contexto do bot
        """
        if user_id not in self._temp_messages:
            return
        
        now = datetime.utcnow().timestamp()
        remaining = []
        cleaned = 0
        
        for msg in self._temp_messages[user_id]:
            if msg["expires_at"] <= now:
                try:
                    await context.bot.delete_message(
                        chat_id=msg["chat_id"],
                        message_id=msg["message_id"],
                    )
                    cleaned += 1
                except Exception:
                    pass  # Mensagem já foi deletada
            else:
                remaining.append(msg)
        
        self._temp_messages[user_id] = remaining
        
        if cleaned > 0:
            logger.debug(f"Limpeza: {cleaned} mensagens de {user_id}")
    
    async def clear_user_history(
        self,
        user_id: int,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        """
        Limpa todo histórico de mensagens do usuário
        
        Args:
            user_id: ID do usuário
            context: Contexto
        """
        # Limpa mensagens do histórico
        if user_id in self._history:
            for msg in self._history[user_id]:
                try:
                    await context.bot.delete_message(
                        chat_id=msg["chat_id"],
                        message_id=msg["message_id"],
                    )
                except Exception:
                    pass
            
            del self._history[user_id]
        
        # Limpa mensagens temporárias
        if user_id in self._temp_messages:
            for msg in self._temp_messages[user_id]:
                try:
                    await context.bot.delete_message(
                        chat_id=msg["chat_id"],
                        message_id=msg["message_id"],
                    )
                except Exception:
                    pass
            
            del self._temp_messages[user_id]
    
    def get_screen_name(self, callback_data: str) -> str:
        """
        Extrai nome da tela do callback_data
        
        Args:
            callback_data: Dados do callback
            
        Returns:
            Nome da tela
        """
        # Mapeamento de ações para telas
        screen_map = {
            "btn_buy_giftcard": "catalog",
            "btn_my_profile": "profile",
            "btn_add_balance": "wallet",
            "btn_history": "history",
            "btn_affiliates": "affiliates",
            "btn_support": "support",
            "menu_main": "menu",
            "back_to_catalog": "catalog",
            "back_to_menu": "menu",
            "go_to_wallet": "wallet",
        }
        
        return screen_map.get(callback_data, "unknown")


# Instância global
navigation_service = NavigationService()
