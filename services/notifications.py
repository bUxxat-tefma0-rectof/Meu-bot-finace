"""
Serviço de Notificações
Envia notificações para o canal configurado
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Serviço para envio de notificações
    
    Envia mensagens para o canal de notificações
    configurado no painel admin.
    """
    
    def __init__(self):
        self.channel_id = settings.NOTIFICATION_CHANNEL_ID
    
    async def send_notification(
        self,
        message: str,
        notification_type: str,
        context=None,
        parse_mode: str = "HTML",
        related_data: Optional[Dict] = None,
    ) -> bool:
        """
        Envia notificação para o canal
        
        Args:
            message: Texto da notificação
            notification_type: Tipo (purchase, pix, etc)
            context: Contexto do bot
            parse_mode: Modo de parse
            related_data: Dados relacionados
            
        Returns:
            Sucesso
        """
        if not settings.NOTIFICATIONS_ENABLED:
            return False
        
        if not self.channel_id:
            logger.warning("Canal de notificações não configurado")
            return False
        
        # Verifica se tipo está habilitado
        if not self._is_type_enabled(notification_type):
            return False
        
        try:
            # Salva no banco
            await self._save_notification(
                notification_type=notification_type,
                message=message,
                related_data=related_data,
            )
            
            # Envia para o Telegram
            if context and context.bot:
                sent_message = await context.bot.send_message(
                    chat_id=self.channel_id,
                    text=message,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True,
                )
                
                # Atualiza com ID da mensagem
                await self._update_notification_sent(sent_message.message_id)
                
                logger.info(f"Notificação enviada: {notification_type}")
                return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {e}")
        
        return False
    
    def _is_type_enabled(self, notification_type: str) -> bool:
        """Verifica se tipo de notificação está habilitado"""
        type_settings = {
            "purchase": settings.NOTIFY_ON_PURCHASE,
            "new_stock": settings.NOTIFY_ON_NEW_STOCK,
            "pix_approved": settings.NOTIFY_ON_PIX_APPROVED,
            "pix_expired": settings.NOTIFY_ON_PIX_EXPIRED,
            "new_user": settings.NOTIFY_ON_NEW_USER,
            "low_stock": settings.NOTIFY_ON_LOW_STOCK,
            "commission": settings.NOTIFY_ON_COMMISSION,
        }
        
        return type_settings.get(notification_type, True)
    
    async def notify_purchase(
        self,
        user_id: int,
        purchase_data: Dict,
        context=None,
    ):
        """
        Notifica compra realizada
        
        Args:
            user_id: ID do comprador
            purchase_data: Dados da compra
            context: Contexto do bot
        """
        message = (
            f"🛒 COMPRA REALIZADA!\n\n"
            f"👤 Cliente: {user_id}\n"
            f"🎁 Produto: {purchase_data.get('product_name', 'N/A')}\n"
            f"💰 Valor: R$ {purchase_data.get('price', 0):.2f}\n"
            f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="purchase",
            context=context,
            related_data={"user_id": user_id, "purchase": purchase_data},
        )
    
    async def notify_new_stock(
        self,
        product_name: str,
        quantity: int,
        context=None,
    ):
        """
        Notifica novo estoque adicionado
        
        Args:
            product_name: Nome do produto
            quantity: Quantidade adicionada
            context: Contexto do bot
        """
        message = (
            f"📦 NOVO ESTOQUE ADICIONADO!\n\n"
            f"🏪 Produto: {product_name}\n"
            f"📦 Quantidade: {quantity} itens\n"
            f"🏃‍♂️ Corra e garanta o seu!\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="new_stock",
            context=context,
            related_data={"product": product_name, "quantity": quantity},
        )
    
    async def notify_pix_approved(
        self,
        user_id: int,
        pix_data: Dict,
        context=None,
    ):
        """
        Notifica PIX aprovado
        
        Args:
            user_id: ID do usuário
            pix_data: Dados do PIX
            context: Contexto do bot
        """
        message = (
            f"💳 PIX APROVADO!\n\n"
            f"👤 Usuário: {user_id}\n"
            f"💰 Valor: R$ {pix_data.get('value', 0):.2f}\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="pix_approved",
            context=context,
            related_data={"user_id": user_id, "pix": pix_data},
        )
    
    async def notify_new_user(
        self,
        user_id: int,
        context=None,
    ):
        """
        Notifica novo usuário
        
        Args:
            user_id: ID do novo usuário
            context: Contexto do bot
        """
        message = (
            f"👤 NOVO USUÁRIO!\n\n"
            f"🆔 ID: {user_id}\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="new_user",
            context=context,
            related_data={"user_id": user_id},
        )
    
    async def notify_low_stock(
        self,
        product_name: str,
        stock_count: int,
        context=None,
    ):
        """
        Notifica estoque baixo
        
        Args:
            product_name: Nome do produto
            stock_count: Quantidade atual
            context: Contexto do bot
        """
        message = (
            f"⚠️ ESTOQUE BAIXO!\n\n"
            f"📦 Produto: {product_name}\n"
            f"📊 Estoque atual: {stock_count} unidades\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="low_stock",
            context=context,
            related_data={"product": product_name, "stock": stock_count},
        )
    
    async def notify_commission(
        self,
        affiliate_id: int,
        commission_data: Dict,
        context=None,
    ):
        """
        Notifica comissão gerada
        
        Args:
            affiliate_id: ID do afiliado
            commission_data: Dados da comissão
            context: Contexto do bot
        """
        message = (
            f"🤝 COMISSÃO GERADA!\n\n"
            f"👤 Afiliado: {affiliate_id}\n"
            f"💰 Valor: R$ {commission_data.get('amount', 0):.2f}\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await self.send_notification(
            message=message,
            notification_type="commission",
            context=context,
            related_data={"affiliate_id": affiliate_id, "commission": commission_data},
        )
    
    async def _save_notification(
        self,
        notification_type: str,
        message: str,
        related_data: Optional[Dict] = None,
    ):
        """Salva notificação no banco"""
        try:
            from database.repositories.notification_repository import NotificationRepository
            repo = NotificationRepository()
            
            await repo.create(
                type=notification_type,
                message=message,
                is_sent=False,
                channel_id=self.channel_id,
                extra_data=str(related_data) if related_data else None,
            )
        except Exception as e:
            logger.error(f"Erro ao salvar notificação: {e}")
    
    async def _update_notification_sent(self, message_id: int):
        """Atualiza notificação como enviada"""
        try:
            from database.repositories.notification_repository import NotificationRepository
            repo = NotificationRepository()
            
            # Busca última notificação não enviada
            notifications = await repo.get_pending_notifications(limit=1)
            
            if notifications:
                await repo.update(
                    notifications[0].id,
                    is_sent=True,
                    sent_at=datetime.utcnow(),
                    message_id=message_id,
                )
        except Exception as e:
            logger.error(f"Erro ao atualizar notificação: {e}")
    
    async def check_pending_notifications(self, context=None):
        """Verifica notificações pendentes (job)"""
        try:
            from database.repositories.notification_repository import NotificationRepository
            repo = NotificationRepository()
            
            pending = await repo.get_pending_notifications(limit=10)
            
            for notification in pending:
                if context and context.bot:
                    try:
                        await context.bot.send_message(
                            chat_id=self.channel_id,
                            text=notification.message,
                            parse_mode="HTML",
                        )
                        
                        await repo.update(
                            notification.id,
                            is_sent=True,
                            sent_at=datetime.utcnow(),
                        )
                    except Exception as e:
                        logger.error(f"Erro ao reenviar notificação: {e}")
        except Exception as e:
            logger.error(f"Erro ao verificar notificações: {e}")
