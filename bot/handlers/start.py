"""
Handler do comando /start
Verificação de canal obrigatório e boas-vindas
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import settings
from database.connection import get_session
from services.users import UserService
from services.messages import MessageService

logger = logging.getLogger(__name__)

BLOCKED_STATE = 1
WELCOME_STATE = 2


async def check_channel_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica se o usuário está inscrito no canal obrigatório"""
    try:
        channel_id = settings.REQUIRED_CHANNEL_ID
        
        if not channel_id:
            return True
        
        if channel_id.startswith("-100"):
            chat_id = int(channel_id)
        elif channel_id.startswith("@"):
            chat_id = channel_id
        else:
            try:
                chat_id = int(channel_id)
            except ValueError:
                return True
        
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        valid_statuses = ["member", "administrator", "creator"]
        return member.status in valid_statuses
        
    except TelegramError as e:
        logger.error(f"Erro ao verificar inscrição no canal: {e}")
        return True
    except ValueError as e:
        logger.error(f"Erro inesperado na verificação: {e}")
        return True
    except Exception as e:
        logger.error(f"Erro inesperado na verificação: {e}")
        return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Ponto de entrada do bot"""
    user = update.effective_user
    user_id = user.id
    
    context.user_data['telegram_id'] = user_id
    context.user_data['username'] = user.username or ""
    context.user_data['first_name'] = user.first_name or ""
    context.user_data['last_name'] = user.last_name or ""
    
    if context.args and len(context.args) > 0:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id:
                context.user_data['referrer_id'] = referrer_id
                logger.info(f"Usuário {user_id} indicado por {referrer_id}")
        except (ValueError, TypeError):
            pass
    
    user_service = UserService()
    await user_service.register_user(
        telegram_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        referrer_id=context.user_data.get('referrer_id')
    )
    
    is_subscribed = await check_channel_subscription(user_id, context)
    
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 ENTRAR NO CANAL", url=settings.REQUIRED_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ VERIFICAR AGORA", callback_data="verify_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        blocked_message = settings.MESSAGES.get("BLOCKED_MESSAGE", settings.MESSAGES["blocked"]).format(
            channel_link=settings.REQUIRED_CHANNEL_LINK
        )
        
        await update.message.reply_text(blocked_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return BLOCKED_STATE
    
    return await show_welcome(update, context)


async def verify_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para verificar inscrição no canal"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_subscribed = await check_channel_subscription(user_id, context)
    
    if is_subscribed:
        await query.message.delete()
        return await show_welcome(update, context)
    else:
        await query.edit_message_text(
            "❌ Você ainda não entrou no canal!\n\n📢 Entre no canal obrigatório e depois clique em VERIFICAR.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 ENTRAR NO CANAL", url=settings.REQUIRED_CHANNEL_LINK)],
                [InlineKeyboardButton("✅ VERIFICAR NOVAMENTE", callback_data="verify_subscription")]
            ])
        )
        return BLOCKED_STATE


async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback do botão de inscrição"""
    query = update.callback_query
    await query.answer("Redirecionando para o canal...")
    return BLOCKED_STATE


async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra mensagem de boas-vindas"""
    user_id = update.effective_user.id
    
    user_service = UserService()
    user_data = await user_service.get_user(user_id)
    
    welcome_msg = settings.MESSAGES.get("WELCOME_MESSAGE", settings.MESSAGES.get("welcome", "Bem-vindo! 🎁")).format(
        telegram_id=user_id,
        saldo=f"{user_data.get('balance', 0):.2f}".replace('.', ','),
        compras=user_data.get('total_purchases', 0)
    )
    
    from bot.keyboards.menu import get_main_menu_keyboard
    keyboard = await get_main_menu_keyboard(context)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(welcome_msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(welcome_msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    if user_data.get('is_new', False):
        from services.notifications import NotificationService
        await NotificationService().notify_new_user(user_id, context)
    
    return ConversationHandler.END
