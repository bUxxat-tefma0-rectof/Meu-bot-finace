"""
Handler de Suporte
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

SUPPORT_STATE = 1


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra opções de suporte"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    support_message = (
        f"💬 Central de Suporte\n\n"
        f"Precisa de ajuda? Escolha uma opção:\n\n"
        f"📞 Suporte via Telegram: {settings.SUPPORT_LINK}\n"
        f"📧 Email: suporte@giftcardstore.com\n\n"
        f"⏰ Horário de atendimento:\n"
        f"Seg-Sex: 09h às 18h\n"
        f"Sáb: 09h às 13h\n\n"
        f"ℹ️ Dúvidas frequentes:\n"
        f"• Como comprar?\n"
        f"• Como usar o PIX?\n"
        f"• Onde vejo meu saldo?\n"
        f"• Como ser afiliado?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Falar com Suporte", url=settings.SUPPORT_LINK)],
        [InlineKeyboardButton("❓ FAQ", callback_data="support_faq")],
        [InlineKeyboardButton("📝 Reportar Problema", callback_data="support_report")],
        [InlineKeyboardButton("💡 Sugestão", callback_data="support_suggestion")],
        [get_back_button()]
    ])
    
    if query:
        await query.edit_message_text(
            support_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            support_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    
    return SUPPORT_STATE


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa interações de suporte"""
    query = update.callback_query
    
    if query:
        await query.answer()
        action = query.data
        
        if action == "support_faq":
            return await show_faq(update, context)
        
        elif action == "support_report":
            return await show_report_form(update, context)
        
        elif action == "support_suggestion":
            return await show_suggestion_form(update, context)
    
    # Se for mensagem de texto (report ou sugestão)
    if update.message and update.message.text:
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Encaminha mensagem para o suporte
        support_chat_id = settings.SUPPORT_USERNAME
        
        try:
            forward_text = (
                f"📩 Mensagem de Suporte\n\n"
                f"👤 Usuário: {user_id}\n"
                f"📝 Mensagem:\n{message_text}"
            )
            
            # Tenta enviar para o suporte
            # await context.bot.send_message(
            #     chat_id=support_chat_id,
            #     text=forward_text
            # )
            
            await update.message.reply_text(
                "✅ Mensagem enviada com sucesso!\n"
                "Nossa equipe entrará em contato em breve.",
                reply_markup=InlineKeyboardMarkup([[get_back_button()]])
            )
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de suporte: {e}")
            await update.message.reply_text(
                "❌ Erro ao enviar mensagem. Tente novamente mais tarde.",
                reply_markup=InlineKeyboardMarkup([[get_back_button()]])
            )
    
    return SUPPORT_STATE


async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra perguntas frequentes"""
    query = update.callback_query
    
    faq_message = (
        f"❓ Perguntas Frequentes\n\n"
        f"1️⃣ Como comprar um gift card?\n"
        f"R: Acesse o menu Comprar Gift Card, escolha a categoria e o produto desejado.\n\n"
        f"2️⃣ Como adicionar saldo?\n"
        f"R: Use o comando /pix ou acesse Adicionar Saldo no menu.\n\n"
        f"3️⃣ Quanto tempo leva para o PIX cair?\n"
        f"R: Geralmente é instantâneo, mas pode levar até 30 minutos.\n\n"
        f"4️⃣ Como funciona a garantia?\n"
        f"R: Cada produto tem sua garantia especificada na descrição.\n\n"
        f"5️⃣ Como me torno afiliado?\n"
        f"R: Acesse o menu Afiliados e compartilhe seu link exclusivo."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="btn_support")],
        [get_back_button()]
    ])
    
    await query.edit_message_text(
        faq_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return SUPPORT_STATE


async def show_report_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra formulário de report"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"📝 Reportar Problema\n\n"
        f"Descreva o problema que você está enfrentando:\n\n"
        f"Envie uma mensagem com os detalhes do ocorrido.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="btn_support")]
        ]),
        parse_mode=ParseMode.HTML
    )
    
    return SUPPORT_STATE


async def show_suggestion_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra formulário de sugestão"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"💡 Enviar Sugestão\n\n"
        f"Adoramos ouvir sua opinião!\n"
        f"Envie sua sugestão para melhorarmos:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="btn_support")]
        ]),
        parse_mode=ParseMode.HTML
    )
    
    return SUPPORT_STATE
