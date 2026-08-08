"""
Handler de Notificações (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.notifications import NotificationService

logger = logging.getLogger(__name__)

NOTIFICATIONS_STATE = 1


async def admin_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia notificações do sistema"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    notification_config = {
        'on_purchase': settings.NOTIFY_ON_PURCHASE,
        'on_new_stock': settings.NOTIFY_ON_NEW_STOCK,
        'on_pix_approved': settings.NOTIFY_ON_PIX_APPROVED,
        'on_pix_expired': settings.NOTIFY_ON_PIX_EXPIRED,
        'on_new_user': settings.NOTIFY_ON_NEW_USER,
        'on_low_stock': settings.NOTIFY_ON_LOW_STOCK,
        'on_commission': settings.NOTIFY_ON_COMMISSION,
    }
    
    message = (
        f"🔔 CONFIGURAÇÕES DE NOTIFICAÇÕES\n\n"
        f"Canal: {settings.NOTIFICATION_CHANNEL_LINK}\n"
        f"Status: {'🟢 Ativo' if settings.NOTIFICATIONS_ENABLED else '🔴 Inativo'}\n\n"
        f"Notificações:\n"
        f"{'✅' if notification_config['on_purchase'] else '❌'} Compra realizada\n"
        f"{'✅' if notification_config['on_new_stock'] else '❌'} Novo estoque\n"
        f"{'✅' if notification_config['on_pix_approved'] else '❌'} PIX aprovado\n"
        f"{'✅' if notification_config['on_pix_expired'] else '❌'} PIX expirado\n"
        f"{'✅' if notification_config['on_new_user'] else '❌'} Novo usuário\n"
        f"{'✅' if notification_config['on_low_stock'] else '❌'} Estoque baixo\n"
        f"{'✅' if notification_config['on_commission'] else '❌'} Comissão gerada\n"
        f"\n⚠️ Estoque baixo: {settings.LOW_STOCK_THRESHOLD} unidades"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Ativar Todas", callback_data="admin_notify_all_on"),
            InlineKeyboardButton("🔕 Desativar Todas", callback_data="admin_notify_all_off"),
        ],
        [
            InlineKeyboardButton("🛒 Compra", callback_data="admin_toggle_notify_purchase"),
            InlineKeyboardButton("📦 Estoque", callback_data="admin_toggle_notify_stock"),
        ],
        [
            InlineKeyboardButton("💳 PIX Aprov.", callback_data="admin_toggle_notify_pix_approved"),
            InlineKeyboardButton("⌛ PIX Exp.", callback_data="admin_toggle_notify_pix_expired"),
        ],
        [
            InlineKeyboardButton("👤 Novo User", callback_data="admin_toggle_notify_new_user"),
            InlineKeyboardButton("⚠️ Est. Baixo", callback_data="admin_toggle_notify_low_stock"),
        ],
        [
            InlineKeyboardButton("🤝 Comissão", callback_data="admin_toggle_notify_commission"),
        ],
        [
            InlineKeyboardButton("📝 Editar Mensagens", callback_data="admin_edit_notification_messages"),
        ],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return NOTIFICATIONS_STATE


async def admin_toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa/desativa notificações específicas"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    action = query.data
    
    notification_service = NotificationService()
    
    if action == "admin_notify_all_on":
        await notification_service.enable_all_notifications(admin_id)
        await query.answer("Todas ativadas!", show_alert=True)
    elif action == "admin_notify_all_off":
        await notification_service.disable_all_notifications(admin_id)
        await query.answer("Todas desativadas!", show_alert=True)
    elif action.startswith("admin_toggle_notify_"):
        notify_type = action.replace("admin_toggle_notify_", "")
        result = await notification_service.toggle_notification(notify_type, admin_id)
        await query.answer(f"Notificação {result['status']}!", show_alert=True)
    
    return await admin_notifications(update, context)
