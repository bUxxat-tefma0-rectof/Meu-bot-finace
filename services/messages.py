"""
Serviço de Mensagens
Gerencia templates de mensagens do bot
"""

import logging
from typing import Dict, Any, Optional

from config import settings

logger = logging.getLogger(__name__)


class MessageService:
    """
    Serviço para gerenciamento de mensagens
    
    Permite editar todas as mensagens do bot
    sem alterar o código fonte.
    """
    
    # Mensagens padrão (podem ser sobrescritas pelo banco)
    DEFAULT_MESSAGES = {
        "welcome": "Olá, {first_name}! Bem-vindo à Loja de Gift Cards! 🎁\n\n"
                   "🆔 Seu ID: {telegram_id}\n"
                   "💰 Saldo: R$ {balance}\n"
                   "🛒 Compras: {total_purchases}",
        
        "blocked": "🚫 Acesso Bloqueado\n\n"
                   "Você precisa entrar no canal para usar o bot.\n"
                   "📢 {channel_link}",
        
        "menu": "📋 Menu Principal\nEscolha uma opção:",
        
        "catalog": "🛒 Selecione a categoria:",
        
        "product": "📦 {name}\n"
                   "💰 Preço: R$ {price}\n"
                   "📦 Estoque: {stock}\n"
                   "📝 {description}",
        
        "insufficient_balance": "🚫 Saldo Insuficiente\n\n"
                                "💰 Precisa: R$ {needed}\n"
                                "💳 Você tem: R$ {balance}",
        
        "pix_generated": "💠 PIX Gerado\n\n"
                         "💰 Valor: R$ {value}\n"
                         "⏳ Expira em: {expires_at}\n\n"
                         "Código PIX:\n{pix_code}",
        
        "pix_approved": "✅ Pagamento Aprovado!\n\n"
                        "💰 Valor: R$ {value}\n"
                        "💳 Novo saldo: R$ {new_balance}",
        
        "pix_expired": "⌛ PIX Expirado\n\n"
                       "O pagamento não foi realizado a tempo.",
        
        "purchase_success": "✅ Compra Realizada!\n\n"
                            "🎁 Produto: {product_name}\n"
                            "💰 Valor: R$ {price}\n"
                            "📦 Conteúdo:\n{delivery_content}",
        
        "profile": "👤 Perfil\n\n"
                   "🆔 ID: {telegram_id}\n"
                   "👤 Nome: {first_name}\n"
                   "💰 Saldo: R$ {balance}\n"
                   "🛒 Compras: {total_purchases}",
        
        "history_empty": "📭 Nenhuma compra realizada.",
        
        "affiliate": "🤝 Programa de Afiliados\n\n"
                     "📌 Seu link:\n{affiliate_link}\n\n"
                     "💰 Comissão: {commission_rate}%\n"
                     "👥 Indicados: {total_referrals}\n"
                     "💵 Ganhos: R$ {total_earnings}",
        
        "support": "💬 Suporte\n\n"
                   "Entre em contato: {support_link}",
        
        "error": "❌ Ocorreu um erro. Tente novamente.",
    }
    
    def __init__(self):
        self._messages = self.DEFAULT_MESSAGES.copy()
    
    async def get_message(self, key: str) -> str:
        """
        Obtém uma mensagem pelo identificador
        
        Args:
            key: Chave da mensagem
            
        Returns:
            Texto da mensagem
        """
        # Tenta buscar do banco primeiro
        try:
            from database.repositories.message_repository import MessageRepository
            repo = MessageRepository()
            msg = await repo.get_by_key(key)
            
            if msg:
                return msg.content
        except Exception as e:
            logger.warning(f"Erro ao buscar mensagem do banco: {e}")
        
        # Fallback para mensagens padrão
        return self._messages.get(key, self._messages["error"])
    
    async def format_message(self, key: str, **kwargs) -> str:
        """
        Obtém e formata uma mensagem
        
        Args:
            key: Chave da mensagem
            **kwargs: Variáveis para substituição
            
        Returns:
            Mensagem formatada
        """
        template = await self.get_message(key)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Variável ausente na mensagem '{key}': {e}")
            return template
        except Exception as e:
            logger.error(f"Erro ao formatar mensagem: {e}")
            return template
    
    async def update_message(
        self,
        key: str,
        content: str,
        admin_id: int,
    ) -> Dict[str, Any]:
        """
        Atualiza uma mensagem
        
        Args:
            key: Chave da mensagem
            content: Novo conteúdo
            admin_id: ID do admin
            
        Returns:
            Resultado
        """
        try:
            from database.repositories.message_repository import MessageRepository
            from database.repositories.audit_repository import AuditRepository
            
            repo = MessageRepository()
            
            # Atualiza ou cria
            existing = await repo.get_by_key(key)
            
            if existing:
                await repo.update(existing.id, content=content)
            else:
                await repo.create(
                    key=key,
                    name=key,
                    content=content,
                )
            
            # Atualiza cache local
            self._messages[key] = content
            
            # Auditoria
            audit_repo = AuditRepository()
            await audit_repo.create_log(
                admin_id=admin_id,
                action="update_message",
                entity_type="message_template",
                entity_id=existing.id if existing else None,
                description=f"Mensagem '{key}' atualizada",
            )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Erro ao atualizar mensagem: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_all_messages(self) -> Dict[str, str]:
        """Retorna todas as mensagens"""
        try:
            from database.repositories.message_repository import MessageRepository
            repo = MessageRepository()
            messages = await repo.get_all()
            
            result = {}
            for msg in messages:
                result[msg.key] = msg.content
            
            return result
        except Exception:
            return self._messages.copy()
    
    async def reset_to_default(self, key: str, admin_id: int) -> Dict[str, Any]:
        """
        Reseta mensagem para o padrão
        
        Args:
            key: Chave da mensagem
            admin_id: ID do admin
            
        Returns:
            Resultado
        """
        default = self.DEFAULT_MESSAGES.get(key)
        
        if default:
            return await self.update_message(key, default, admin_id)
        
        return {"success": False, "error": "Mensagem padrão não encontrada"}
