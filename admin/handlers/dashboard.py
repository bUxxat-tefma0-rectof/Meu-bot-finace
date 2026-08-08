"""
Handler do Dashboard Administrativo
Visão geral do sistema
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.users import UserService
from services.products import ProductService
from services.orders import OrderService
from services.wallet import WalletService
from services.affiliates import AffiliateService

logger = logging.getLogger(__name__)

DASHBOARD_STATE = 1


async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dashboard principal do administrador"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Verifica permissão
    if not settings.is_admin(user_id):
        if query:
            await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    if query:
        await query.answer()
    
    # Busca estatísticas
    user_service = UserService()
    product_service = ProductService()
    order_service = OrderService()
    wallet_service = WalletService()
    affiliate_service = AffiliateService()
    
    # Dados para o dashboard
    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_users': await user_service.get_total_users(),
        'active_users_today': await user_service.get_active_users_today(),
        'sales_today': await order_service.get_sales_count_today(),
        'sales_total': await order_service.get_total_sales_count(),
        'revenue_today': await order_service.get_revenue_today(),
        'revenue_total': await order_service.get_total_revenue(),
        'pix_today': await wallet_service.get_pix_count_today(),
        'pix_pending': await wallet_service.get_pending_pix_count(),
        'pix_approved': await wallet_service.get_approved_pix_count_today(),
        'products_sold': await product_service.get_total_sold(),
        'total_stock': await product_service.get_total_stock(),
        'products_sold_out': await product_service.get_sold_out_count(),
        'total_affiliates': await affiliate_service.get_total_affiliates(),
        'total_commissions': await affiliate_service.get_total_commissions(),
    }
    
    # Mensagem do dashboard
    dashboard_message = (
        f"📊 DASHBOARD ADMINISTRATIVO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 USUÁRIOS\n"
        f"├ Total: {stats['total_users']}\n"
        f"└ Ativos hoje: {stats['active_users_today']}\n\n"
        f"🛒 VENDAS\n"
        f"├ Hoje: {stats['sales_today']}\n"
        f"├ Total: {stats['sales_total']}\n"
        f"├ Faturamento hoje: R$ {stats['revenue_today']:.2f}\n"
        f"└ Faturamento total: R$ {stats['revenue_total']:.2f}\n\n"
        f"💳 PIX\n"
        f"├ Hoje: {stats['pix_today']}\n"
        f"├ Pendentes: {stats['pix_pending']}\n"
        f"└ Aprovados hoje: {stats['pix_approved']}\n\n"
        f"📦 ESTOQUE\n"
        f"├ Produtos vendidos: {stats['products_sold']}\n"
        f"├ Estoque total: {stats['total_stock']}\n"
        f"└ Produtos esgotados: {stats['products_sold_out']}\n\n"
        f"🤝 AFILIADOS\n"
        f"├ Total: {stats['total_affiliates']}\n"
        f"└ Comissões: R$ {stats['total_commissions']:.2f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    
    # Teclado do admin
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Usuários", callback_data="admin_users")],
        [InlineKeyboardButton("🛒 Produtos", callback_data="admin_products")],
        [InlineKeyboardButton("📦 Estoque", callback_data="admin_stock")],
        [InlineKeyboardButton("💳 Pagamentos", callback_data="admin_payments")],
        [InlineKeyboardButton("🤝 Afiliados", callback_data="admin_affiliates")],
        [InlineKeyboardButton("📢 Notificações", callback_data="admin_notifications")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data="admin_settings")],
        [InlineKeyboardButton("🔐 Administradores", callback_data="admin_admins")],
        [InlineKeyboardButton("📋 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("🔄 Atualizar", callback_data="admin_refresh_dashboard")],
    ])
    
    if query:
        await query.edit_message_text(
            dashboard_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            dashboard_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    return DASHBOARD_STATE


async def refresh_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atualiza o dashboard"""
    return await admin_dashboard(update, context)
