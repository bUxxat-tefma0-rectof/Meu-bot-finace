"""
Handler de Gerenciamento de Pagamentos (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.wallet import WalletService

logger = logging.getLogger(__name__)

PAYMENTS_LIST_STATE = 1
PAYMENT_DETAIL_STATE = 2


async def admin_payments_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todas as transações"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    # Filtro padrão: todos
    filter_status = context.user_data.get('payments_filter', 'all')
    page = context.user_data.get('payments_page', 1)
    
    wallet_service = WalletService()
    result = await wallet_service.get_transactions(
        status=filter_status,
        page=page,
        per_page=10
    )
    
    transactions = result['transactions']
    total = result['total']
    total_pages = result['total_pages']
    
    if not transactions:
        message = "📭 Nenhuma transação encontrada."
    else:
        message = f"💳 TRANSAÇÕES ({total})\n\n"
        
        for trans in transactions:
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'expired': '⌛',
                'cancelled': '❌',
            }.get(trans['status'], '❓')
            
            message += (
                f"🆔 #{trans['id']} {status_emoji}\n"
                f"👤 Cliente: {trans.get('user_name', 'N/A')}\n"
                f"💰 Valor: R$ {trans['value']:.2f}\n"
                f"📅 {trans['created_at']}\n\n"
            )
        
        message += f"📄 Página {page} de {total_pages}"
    
    # Filtros
    filters = [
        ("Todos", "all"),
        ("Pendentes", "pending"),
        ("Pagos", "approved"),
        ("Expirados", "expired"),
        ("Cancelados", "cancelled"),
    ]
    
    keyboard_buttons = []
    
    # Botões de filtro
    filter_row = []
    for name, status in filters:
        prefix = "🔵 " if filter_status == status else ""
        filter_row.append(
            InlineKeyboardButton(f"{prefix}{name}", callback_data=f"admin_filter_{status}")
        )
    keyboard_buttons.append(filter_row)
    
    # Navegação
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"admin_payments_page_{page - 1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"admin_payments_page_{page + 1}"))
    if nav_row:
        keyboard_buttons.append(nav_row)
    
    keyboard_buttons.append([
        InlineKeyboardButton("🔍 Ver Detalhes", callback_data="admin_payment_detail"),
        InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_back_to_dashboard"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return PAYMENTS_LIST_STATE


async def admin_payment_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aplica filtro nas transações"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    filter_status = query.data.replace("admin_filter_", "")
    context.user_data['payments_filter'] = filter_status
    context.user_data['payments_page'] = 1
    
    return await admin_payments_list(update, context)


async def admin_payment_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra detalhes de uma transação"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    await query.edit_message_text(
        "🆔 Digite o ID da transação:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_payments_list")]
        ])
    )
    
    return PAYMENT_DETAIL_STATE


async def admin_payment_show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe detalhes da transação"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    try:
        trans_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")
        return PAYMENT_DETAIL_STATE
    
    wallet_service = WalletService()
    transaction = await wallet_service.get_transaction_detail(trans_id)
    
    if not transaction:
        await update.message.reply_text(
            "❌ Transação não encontrada.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_payments_list")]
            ])
        )
        return PAYMENT_DETAIL_STATE
    
    detail_message = (
        f"💳 DETALHES DA TRANSAÇÃO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {transaction['id']}\n"
        f"👤 Cliente: {transaction.get('user_name', 'N/A')} ({transaction['user_id']})\n"
        f"💰 Valor: R$ {transaction['value']:.2f}\n"
        f"💠 Provedor: {transaction.get('provider', 'PIX')}\n"
        f"📊 Status: {transaction['status']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Criado em: {transaction['created_at']}\n"
        f"🕐 Expira em: {transaction.get('expires_at', 'N/A')}\n"
        f"✅ Aprovado em: {transaction.get('approved_at', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 ID Externo: {transaction.get('external_id', 'N/A')}\n"
        f"📋 Código PIX: {transaction.get('pix_code', 'N/A')[:50]}...\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"admin_approve_payment_{transaction['id']}") if transaction['status'] == 'pending'
            else InlineKeyboardButton("❌ Cancelar", callback_data=f"admin_cancel_payment_{transaction['id']}"),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_payments_list")],
    ])
    
    await update.message.reply_text(
        detail_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return ConversationHandler.END
