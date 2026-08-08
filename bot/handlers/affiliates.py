"""
Handler do Sistema de Afiliados
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

AFFILIATE_STATE = 1


async def affiliates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informações do programa de afiliados"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    from services.affiliates import AffiliateService
    service = AffiliateService()
    data = await service.get_affiliate_info(user_id)
    
    link = f"https://t.me/{settings.BOT_USERNAME}?start={user_id}"
    
    msg = (
        f"🤝 Programa de Afiliados\n\n"
        f"📌 Seu link exclusivo:\n<code>{link}</code>\n\n"
        f"💰 Comissão: {settings.AFFILIATE_COMMISSION_PERCENT}%\n"
        f"💵 Depósito mínimo: R$ {settings.AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION:.2f}\n\n"
    )
    
    if data:
        msg += (
            f"📊 Suas Estatísticas:\n"
            f"👥 Indicados: {data['total_referrals']}\n"
            f"💰 Ganhos Totais: R$ {data['total_earnings']:.2f}\n"
            f"💳 Saldo Disponível: R$ {data['available_balance']:.2f}\n\n"
        )
    
    msg += "🚀 Compartilhe seu link e comece a lucrar!"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Ver Indicados", callback_data="affiliate_referrals")],
        [InlineKeyboardButton("💰 Histórico de Comissões", callback_data="affiliate_commissions")],
        [get_back_button()],
    ])
    
    context.user_data['affiliate_link'] = link
    
    if query:
        await query.edit_message_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await update.message.reply_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    return AFFILIATE_STATE


async def affiliates_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa callbacks de afiliados"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "affiliate_referrals":
        return await show_referrals(update, context)
    elif action == "affiliate_commissions":
        return await show_commissions(update, context)
    
    return AFFILIATE_STATE


async def show_referrals(update, context):
    query = update.callback_query
    from services.affiliates import AffiliateService
    refs = await AffiliateService().get_referrals(update.effective_user.id)
    
    if not refs:
        msg = "📭 Você ainda não tem indicados."
    else:
        msg = f"👥 Seus Indicados ({len(refs)}):\n\n"
        for i, r in enumerate(refs[:10], 1):
            msg += f"{i}. {r.get('first_name', 'Usuário')}\n   💰 Depósitos: R$ {r.get('total_deposits', 0):.2f}\n\n"
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="btn_affiliates")],
        [get_back_button()]
    ]))
    return AFFILIATE_STATE


async def show_commissions(update, context):
    query = update.callback_query
    from services.affiliates import AffiliateService
    comms = await AffiliateService().get_commission_history(update.effective_user.id)
    
    if not comms:
        msg = "📭 Nenhuma comissão recebida ainda."
    else:
        msg = "💰 Histórico de Comissões:\n\n"
        for c in comms[:10]:
            msg += f"📅 {c['date']}\n👤 {c['referred_name']}\n💵 Depósito: R$ {c['deposit_value']:.2f}\n🤝 Comissão: R$ {c['commission_value']:.2f}\n\n"
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="btn_affiliates")],
        [get_back_button()]
    ]))
    return AFFILIATE_STATE
