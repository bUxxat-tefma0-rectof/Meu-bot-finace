"""
Handler de Logs (Admin)
Visualização de logs de auditoria
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from database.repositories.audit_repository import AuditRepository
from admin.keyboards.admin_menu import get_admin_back_button

logger = logging.getLogger(__name__)

ADMIN_LOGS_STATE = 1
ITEMS_PER_PAGE = 10


async def admin_logs_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista logs de auditoria"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    page = context.user_data.get('admin_logs_page', 1)
    filter_entity = context.user_data.get('admin_logs_filter', None)
    
    audit_repo = AuditRepository()
    
    result = await audit_repo.get_logs(
        entity_type=filter_entity,
        page=page,
        per_page=ITEMS_PER_PAGE,
    )
    
    logs = result['logs']
    total = result['total']
    total_pages = result['total_pages']
    
    if not logs:
        message = "📋 Nenhum log encontrado."
    else:
        message = f"📋 LOGS DE AUDITORIA ({total})\n\n"
        
        for log in logs:
            log_data = log.to_dict()
            message += (
                f"🕐 {log_data['created_at']}\n"
                f"👤 Admin: {log_data['admin_id'] or 'Sistema'}\n"
                f"🔧 Ação: {log_data['action']}\n"
                f"📦 {log_data['entity_type']}"
            )
            
            if log_data.get('entity_id'):
                message += f" #{log_data['entity_id']}"
            
            if log_data.get('description'):
                message += f"\n📝 {log_data['description'][:100]}"
            
            message += "\n\n"
        
        message += f"📄 Página {page} de {total_pages}"
    
    # Teclado
    keyboard_buttons = []
    
    # Filtros
    filter_buttons = [
        ("Todos", None),
        ("Usuários", "user"),
        ("Produtos", "product"),
        ("Estoque", "stock_item"),
        ("Pagamentos", "payment"),
        ("Config", "system_setting"),
    ]
    
    filter_row = []
    for name, entity in filter_buttons:
        prefix = "🔵 " if filter_entity == entity else ""
        filter_row.append(
            InlineKeyboardButton(
                f"{prefix}{name}",
                callback_data=f"admin_logs_filter_{entity or 'all'}"
            )
        )
    keyboard_buttons.append(filter_row[:3])
    if len(filter_row) > 3:
        keyboard_buttons.append(filter_row[3:])
    
    # Navegação
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton("⬅️", callback_data=f"admin_logs_page_{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton("➡️", callback_data=f"admin_logs_page_{page + 1}")
        )
    if nav_row:
        keyboard_buttons.append(nav_row)
    
    keyboard_buttons.append([
        InlineKeyboardButton("🗑️ Limpar Logs Antigos", callback_data="admin_logs_clear"),
    ])
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    
    return ADMIN_LOGS_STATE


async def admin_logs_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aplica filtro nos logs"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    filter_value = query.data.replace("admin_logs_filter_", "")
    
    if filter_value == "all":
        context.user_data['admin_logs_filter'] = None
    else:
        context.user_data['admin_logs_filter'] = filter_value
    
    context.user_data['admin_logs_page'] = 1
    
    return await admin_logs_list(update, context)


async def admin_logs_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navegação de páginas"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    page = int(query.data.replace("admin_logs_page_", ""))
    context.user_data['admin_logs_page'] = page
    
    return await admin_logs_list(update, context)


async def admin_logs_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpa logs antigos"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer("Limpando logs...")
    
    from datetime import datetime, timedelta
    
    audit_repo = AuditRepository()
    cutoff = datetime.utcnow() - timedelta(days=30)
    deleted = await audit_repo.delete_old_logs(cutoff)
    
    await query.edit_message_text(
        f"✅ {deleted} logs antigos (30+ dias) foram removidos.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_logs_list")],
        ])
    )
    
    return ADMIN_LOGS_STATE
