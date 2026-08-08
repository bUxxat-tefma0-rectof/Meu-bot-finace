"""
Handler da Carteira/Saldo
Gerencia adição de saldo e redireciona para PIX
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.users import UserService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

WALLET_STATE = 1
PIX_VALUE_STATE = 2


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu da carteira"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Busca saldo
    user_service = UserService()
    user_data = await user_service.get_user(user_id)
    balance = user_data.get('balance', 0)
    
    wallet_message = (
        f"💳 Minha Carteira\n\n"
        f"💰 Saldo Atual: R$ {balance:.2f}\n\n"
        f"Escolha a forma de pagamento:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💠 PIX", callback_data="add_balance_pix")],
        [InlineKeyboardButton("💬 Suporte", url=settings.SUPPORT_LINK)],
        [get_back_button()]
    ])
    
    if query:
        await query.edit_message_text(
            wallet_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            wallet_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    return WALLET_STATE


async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia processo de adicionar saldo via PIX"""
    query = update.callback_query
    
    if query:
        await query.answer()
        
        if query.data == "add_balance_pix":
            pix_message = settings.PIX_MESSAGE.format(
                min_value=f"{settings.PIX_MIN_VALUE:.2f}",
                max_value=f"{settings.PIX_MAX_VALUE:.2f}",
                expiration=settings.PIX_EXPIRATION_MINUTES
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Valores Rápidos", callback_data="quick_values")],
                [get_back_button()]
            ])
            
            await query.edit_message_text(
                pix_message,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
            return PIX_VALUE_STATE
        
        elif query.data == "quick_values":
            # Valores pré-definidos
            quick_values = [30, 50, 100, 200, 500]
            keyboard_buttons = []
            
            for value in quick_values:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"💵 R$ {value:.2f}",
                        callback_data=f"pix_value_{value}"
                    )
                ])
            
            keyboard_buttons.append([get_back_button()])
            
            await query.edit_message_text(
                "💰 Escolha um valor rápido:",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                parse_mode=ParseMode.HTML
            )
            
            return PIX_VALUE_STATE
    
    return WALLET_STATE


async def process_pix_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o valor do PIX e redireciona"""
    from bot.handlers.pix import generate_pix
    
    value = None
    
    # Verifica se é callback de valor rápido
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("pix_value_"):
            value = float(query.data.replace("pix_value_", ""))
    else:
        # Valor digitado manualmente
        try:
            value = float(update.message.text.replace(",", "."))
        except ValueError:
            await update.message.reply_text(
                "❌ Valor inválido. Digite apenas números.\nEx: 50",
                reply_markup=InlineKeyboardMarkup([[get_back_button()]])
            )
            return PIX_VALUE_STATE
    
    if value:
        # Valida valor
        is_valid, error_msg = settings.validate_pix_value(value)
        
        if not is_valid:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"❌ {error_msg}",
                    reply_markup=InlineKeyboardMarkup([[get_back_button()]])
                )
            else:
                await update.message.reply_text(
                    f"❌ {error_msg}",
                    reply_markup=InlineKeyboardMarkup([[get_back_button()]])
                )
            return PIX_VALUE_STATE
        
        # Gera PIX
        context.user_data['pix_value'] = value
        return await generate_pix(update, context)
    
    return PIX_VALUE_STATE
