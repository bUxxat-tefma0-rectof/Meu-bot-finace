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

# Estados da conversação
BLOCKED_STATE = 1
WELCOME_STATE = 2

async def check_channel_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica se o usuário está inscrito no canal obrigatório"""
    try:
        channel_id = settings.REQUIRED_CHANNEL_ID
        
        # Verifica usando o ID do canal
        if channel_id.startswith("-100"):
            chat_id = int(channel_id)
        elif channel_id.startswith("@"):
            chat_id = channel_id
        else:
            chat_id = int(channel_id)
        
        member = await context.bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Verifica se o status é válido (member, administrator, creator)
        valid_statuses = ["member", "administrator", "creator"]
        is_subscribed = member.status in valid_statuses
        
        logger.info(f"Verificação de canal para user {user_id}: {member.status} - Inscrito: {is_subscribed}")
        
        return is_subscribed
        
    except TelegramError as e:
        logger.error(f"Erro ao verificar inscrição no canal: {e}")
        # Se der erro na verificação (canal não encontrado, etc), libera o acesso
        return True
    except Exception as e:
        logger.error(f"Erro inesperado na verificação: {e}")
        return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Ponto de entrada do bot"""
    user = update.effective_user
    user_id = user.id
    
    # Armazena dados do usuário no context
    context.user_data['telegram_id'] = user_id
    context.user_data['username'] = user.username or ""
    context.user_data['first_name'] = user.first_name or ""
    context.user_data['last_name'] = user.last_name or ""
    
    # Verifica se veio de link de afiliado
    if context.args and len(context.args) > 0:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id:  # Não pode se auto-indicar
                context.user_data['referrer_id'] = referrer_id
                logger.info(f"Usuário {user_id} indicado por {referrer_id}")
        except (ValueError, TypeError):
            pass
    
    # Inicializa serviços
    user_service = UserService()
    
    # Registra ou atualiza usuário no banco
    await user_service.register_user(
        telegram_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        referrer_id=context.user_data.get('referrer_id')
    )
    
    # Verifica inscrição no canal
    is_subscribed = await check_channel_subscription(user_id, context)
    
    if not is_subscribed:
        # Usuário não inscrito - mostra mensagem de bloqueio
        keyboard = [
            [InlineKeyboardButton("📢 ENTRAR NO CANAL", url=settings.REQUIRED_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ VERIFICAR AGORA", callback_data="verify_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        blocked_message = settings.BLOCKED_MESSAGE.format(
            channel_link=settings.REQUIRED_CHANNEL_LINK
        )
        
        await update.message.reply_text(
            blocked_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        return BLOCKED_STATE
    
    # Usuário inscrito - mostra boas-vindas
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
            "❌ Você ainda não entrou no canal!\n\n"
            "📢 Entre no canal obrigatório e depois clique em VERIFICAR.",
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
    
    # Busca dados do usuário
    user_service = UserService()
    user_data = await user_service.get_user(user_id)
    
    # Formata mensagem de boas-vindas
    welcome_msg = settings.WELCOME_MESSAGE.format(
        telegram_id=user_id,
        saldo=f"{user_data.get('balance', 0):.2f}".replace('.', ','),
        compras=user_data.get('total_purchases', 0)
    )
    
    # Teclado do menu principal
    from bot.keyboards.menu import get_main_menu_keyboard
    keyboard = await get_main_menu_keyboard(context)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            welcome_msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            welcome_msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    # Notifica novo usuário
    if user_data.get('is_new', False):
        from services.notifications import NotificationService
        notification_service = NotificationService()
        await notification_service.notify_new_user(user_id, context)
    
    return ConversationHandler.END
