"""
Handler de Afiliados (Admin)
Gerencia afiliados, comissões e estatísticas
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.affiliates import AffiliateService
from admin.keyboards.admin_menu import get_admin_back_button

logger = logging.getLogger(__name__)

ADMIN_AFFILIATES_STATE = 1
ITEMS_PER_PAGE = 10


async def admin_affiliates_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista afiliados e estatísticas"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    page = context.user_data.get('admin_affiliates_page', 1)
    
    affiliate_service = AffiliateService()
    
    # Estatísticas gerais
    total_affiliates = await affiliate_service.get_total_affiliates()
    total_commissions = await affiliate_service.get_total_commissions()
    
    message = (
        f"🤝 GERENCIAR AFILIADOS\n\n"
        f"📊 Estatísticas Gerais:\n"
        f"👥 Total de Afiliados: {total_affiliates}\n"
        f"💰 Total em Comissões: R$ {total_commissions:.2f}\n"
        f"📈 Taxa de Comissão: {settings.AFFILIATE_COMMISSION_PERCENT}%\n"
        f"💵 Depósito Mínimo: R$ {settings.AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION:.2f}\n\n"
        f"Escolha uma ação:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏆 Top Afiliados", callback_data="admin_affiliates_top"),
            InlineKeyboardButton("💰 Comissões", callback_data="admin_affiliates_commissions"),
        ],
        [
            InlineKeyboardButton("🔍 Buscar Afiliado", callback_data="admin_affiliates_search"),
            InlineKeyboardButton("📊 Relatório", callback_data="admin_affiliates_report"),
        ],
        [
            InlineKeyboardButton("⚙️ Configurar Comissão", callback_data="admin_affiliates_settings"),
        ],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_AFFILIATES_STATE


async def admin_affiliates_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top afiliados"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    # Busca top afiliados (mock - seria implementado no repositório)
    message = (
        f"🏆 TOP AFILIADOS\n\n"
        f"Esta funcionalidade está em desenvolvimento.\n"
        f"Em breve você poderá ver o ranking completo."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_affiliates_list")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_AFFILIATES_STATE


async def admin_affiliates_commissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Histórico de comissões"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    affiliate_service = AffiliateService()
    
    message = (
        f"💰 HISTÓRICO DE COMISSÕES\n\n"
        f"Total pago: R$ {await affiliate_service.get_total_commissions():.2f}\n\n"
        f"Funcionalidade completa em desenvolvimento."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_affiliates_list")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_AFFILIATES_STATE


async def admin_affiliates_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configurações de comissão"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    message = (
        f"⚙️ CONFIGURAÇÕES DE COMISSÃO\n\n"
        f"Taxa atual: {settings.AFFILIATE_COMMISSION_PERCENT}%\n"
        f"Depósito mínimo: R$ {settings.AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION:.2f}\n\n"
        f"Para alterar, use o comando:\n"
        f"/config_commission <percentual> <minimo>\n\n"
        f"Exemplo: /config_commission 15 50"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_affiliates_list")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_AFFILIATES_STATE
