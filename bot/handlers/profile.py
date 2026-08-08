"""
Handler de Perfil do Usuário
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from services.users import UserService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

PROFILE_STATE = 1


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o perfil do usuário"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Busca dados completos
    user_service = UserService()
    user_data = await user_service.get_user_full_data(user_id)
    
    if not user_data:
        message = "❌ Erro ao carregar perfil."
        keyboard = InlineKeyboardMarkup([[get_back_button()]])
        
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(message, reply_markup=keyboard)
        
        return ConversationHandler.END
    
    # Monta perfil
    profile_message = (
        f"👤 Meu Perfil\n\n"
        f"🆔 ID: {user_data['telegram_id']}\n"
        f"👤 Nome: {user_data['first_name']}\n"
        f"📝 Username: @{user_data['username'] or 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo: R$ {user_data['balance']:.2f}\n"
        f"🛒 Compras: {user_data['total_purchases']}\n"
        f"💸 Total Gasto: R$ {user_data['total_spent']:.2f}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📅 Membro desde: {user_data['created_at']}\n"
        f"🕐 Última atividade: {user_data['last_activity']}\n"
    )
    
    # Se for afiliado, mostra ganhos
    if user_data.get('affiliate_earnings', 0) > 0:
        profile_message += (
            f"━━━━━━━━━━━━━━━━\n"
            f"🤝 Ganhos como Afiliado: R$ {user_data['affiliate_earnings']:.2f}\n"
            f"👥 Indicados: {user_data.get('referral_count', 0)}\n"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Adicionar Saldo", callback_data="go_to_wallet")],
        [InlineKeyboardButton("📜 Histórico de Compras", callback_data="btn_history")],
        [InlineKeyboardButton("🤝 Afiliados", callback_data="btn_affiliates")],
        [get_back_button()]
    ])
    
    if query:
        await query.edit_message_text(
            profile_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            profile_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    return PROFILE_STATE


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa callbacks do perfil"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("profile_", "")
    
    if action == "back":
        from bot.handlers.menu import menu_command
        return await menu_command(update, context)
    
    return PROFILE_STATE
