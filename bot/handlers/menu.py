"""
Handler do Menu Principal
Gerencia navegação e botões do menu
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.users import UserService
from services.messages import MessageService
from bot.keyboards.menu import get_main_menu_keyboard, get_back_button

logger = logging.getLogger(__name__)

# Estados
MENU_MAIN = 1

# Ações dos botões
BUTTON_ACTIONS = {
    "buy_giftcard": "catalog",
    "my_profile": "profile",
    "add_balance": "wallet",
    "history": "history",
    "affiliates": "affiliates",
    "support": "support",
}


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /menu - Mostra o menu principal"""
    user_id = update.effective_user.id
    
    # Busca dados do usuário
    user_service = UserService()
    user_data = await user_service.get_user(user_id)
    
    # Mensagem do menu
    menu_message = (
        f"📋 Menu Principal\n\n"
        f"👤 {user_data.get('first_name', 'Usuário')}\n"
        f"💰 Saldo: R$ {user_data.get('balance', 0):.2f}\n"
        f"🛒 Compras: {user_data.get('total_purchases', 0)}\n\n"
        f"Escolha uma opção:"
    )
    
    keyboard = await get_main_menu_keyboard(context)
    
    if update.message:
        await update.message.reply_text(
            menu_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            menu_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    return MENU_MAIN


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para retornar ao menu"""
    query = update.callback_query
    await query.answer()
    
    return await menu_command(update, context)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa cliques nos botões do menu"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("btn_", "")
    
    # Mapeia ação para o handler correto
    action_map = {
        "buy_giftcard": handle_catalog,
        "my_profile": handle_profile,
        "add_balance": handle_wallet,
        "history": handle_history,
        "affiliates": handle_affiliates,
        "support": handle_support,
    }
    
    handler = action_map.get(action)
    if handler:
        return await handler(update, context)
    
    return MENU_MAIN


async def handle_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para o catálogo"""
    from bot.handlers.catalog import catalog_command
    return await catalog_command(update, context)


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para o perfil"""
    from bot.handlers.profile import profile_command
    return await profile_command(update, context)


async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para carteira"""
    from bot.handlers.wallet import wallet_menu
    return await wallet_menu(update, context)


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para histórico"""
    from bot.handlers.history import history_command
    return await history_command(update, context)


async def handle_affiliates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para afiliados"""
    from bot.handlers.affiliates import affiliates_command
    return await affiliates_command(update, context)


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona para suporte"""
    from bot.handlers.support import support_command
    return await support_command(update, context)
