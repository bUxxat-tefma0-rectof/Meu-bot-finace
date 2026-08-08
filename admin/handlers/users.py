"""
Handler de Gerenciamento de Usuários (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.users import UserService

logger = logging.getLogger(__name__)

USERS_LIST_STATE = 1
USER_DETAIL_STATE = 2
USER_EDIT_STATE = 3
ITEMS_PER_PAGE = 10


async def admin_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os usuários"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not settings.is_admin(user_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    page = context.user_data.get('admin_users_page', 1)
    search = context.user_data.get('admin_users_search', '')
    
    user_service = UserService()
    
    if search:
        result = await user_service.search_users(search, page=page, per_page=ITEMS_PER_PAGE)
    else:
        result = await user_service.get_all_users(page=page, per_page=ITEMS_PER_PAGE)
    
    users = result['users']
    total = result['total']
    total_pages = result['total_pages']
    
    if not users:
        message = "📭 Nenhum usuário encontrado."
    else:
        message = f"👥 USUÁRIOS ({total})\n\n"
        
        for i, user in enumerate(users, 1):
            num = (page - 1) * ITEMS_PER_PAGE + i
            status = "🟢" if user.get('is_active', True) else "🔴"
            message += (
                f"{num}. {status} {user.get('first_name', 'N/A')}\n"
                f"   🆔 ID: {user['telegram_id']}\n"
                f"   💰 Saldo: R$ {user.get('balance', 0):.2f}\n"
                f"   🛒 Compras: {user.get('total_purchases', 0)}\n\n"
            )
        
        message += f"📄 Página {page} de {total_pages}"
    
    # Teclado
    keyboard_buttons = []
    
    # Navegação
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_users_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("🔍 Buscar", callback_data="admin_users_search"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_users_page_{page + 1}"))
    keyboard_buttons.append(nav_buttons)
    
    # Botões de ação
    keyboard_buttons.append([
        InlineKeyboardButton("➕ Adicionar Saldo", callback_data="admin_users_add_balance"),
        InlineKeyboardButton("🚫 Bloquear/Desbloquear", callback_data="admin_users_toggle_block"),
    ])
    
    keyboard_buttons.append([
        InlineKeyboardButton("📊 Exportar", callback_data="admin_users_export"),
        InlineKeyboardButton("📋 Ver Detalhes", callback_data="admin_users_detail"),
    ])
    
    keyboard_buttons.append([InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return USERS_LIST_STATE


async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra detalhes de um usuário específico"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    # Se for navegação de página
    if query.data.startswith("admin_users_page_"):
        page = int(query.data.replace("admin_users_page_", ""))
        context.user_data['admin_users_page'] = page
        return await admin_users_list(update, context)
    
    # Se for busca
    if query.data == "admin_users_search":
        await query.edit_message_text(
            "🔍 Digite o ID, nome ou username do usuário:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_users_cancel_search")]
            ])
        )
        return USER_DETAIL_STATE
    
    # Pede ID do usuário para ver detalhes
    if query.data == "admin_users_detail":
        await query.edit_message_text(
            "🆔 Digite o ID do usuário para ver detalhes:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_users_list")]
            ])
        )
        return USER_DETAIL_STATE
    
    return USERS_LIST_STATE


async def admin_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa entrada de texto para busca/detalhes"""
    user_id = update.effective_user.id
    
    if not settings.is_admin(user_id):
        return ConversationHandler.END
    
    text = update.message.text
    
    # Verifica se é cancelamento
    if text.lower() == "cancelar":
        return await admin_users_list(update, context)
    
    # Tenta encontrar usuário
    user_service = UserService()
    
    # Busca por ID ou username
    try:
        search_id = int(text)
        user_data = await user_service.get_user_full_data(search_id)
    except ValueError:
        # Busca por username
        user_data = await user_service.get_user_by_username(text.replace("@", ""))
    
    if not user_data:
        await update.message.reply_text(
            "❌ Usuário não encontrado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_users_list")]
            ])
        )
        return USER_DETAIL_STATE
    
    # Mostra detalhes do usuário
    detail_message = (
        f"👤 DETALHES DO USUÁRIO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user_data['telegram_id']}\n"
        f"👤 Nome: {user_data['first_name']} {user_data.get('last_name', '')}\n"
        f"📝 Username: @{user_data.get('username', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo: R$ {user_data.get('balance', 0):.2f}\n"
        f"🛒 Compras: {user_data.get('total_purchases', 0)}\n"
        f"💸 Total Gasto: R$ {user_data.get('total_spent', 0):.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤝 Indicados: {user_data.get('referral_count', 0)}\n"
        f"💰 Ganhos Afiliado: R$ {user_data.get('affiliate_earnings', 0):.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Cadastro: {user_data.get('created_at', 'N/A')}\n"
        f"🕐 Última atividade: {user_data.get('last_activity', 'N/A')}\n"
        f"🚫 Bloqueado: {'Sim' if user_data.get('is_blocked') else 'Não'}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Adicionar Saldo", callback_data=f"admin_add_balance_{user_data['telegram_id']}"),
            InlineKeyboardButton("💸 Remover Saldo", callback_data=f"admin_remove_balance_{user_data['telegram_id']}"),
        ],
        [
            InlineKeyboardButton("🚫 Bloquear", callback_data=f"admin_block_user_{user_data['telegram_id']}") if not user_data.get('is_blocked')
            else InlineKeyboardButton("✅ Desbloquear", callback_data=f"admin_unblock_user_{user_data['telegram_id']}"),
        ],
        [
            InlineKeyboardButton("📜 Histórico", callback_data=f"admin_user_history_{user_data['telegram_id']}"),
            InlineKeyboardButton("💳 Depósitos", callback_data=f"admin_user_deposits_{user_data['telegram_id']}"),
        ],
        [InlineKeyboardButton("⬅️ Voltar à Lista", callback_data="admin_users_list")],
    ])
    
    await update.message.reply_text(
        detail_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return USER_DETAIL_STATE


async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona saldo a um usuário"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    target_user_id = int(query.data.split("_")[-1])
    context.user_data['admin_target_user'] = target_user_id
    context.user_data['admin_action'] = 'add_balance'
    
    await query.edit_message_text(
        f"💰 Digite o valor para ADICIONAR ao saldo do usuário {target_user_id}:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin_user_detail_{target_user_id}")]
        ])
    )
    
    return USER_EDIT_STATE


async def admin_remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove saldo de um usuário"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    target_user_id = int(query.data.split("_")[-1])
    context.user_data['admin_target_user'] = target_user_id
    context.user_data['admin_action'] = 'remove_balance'
    
    await query.edit_message_text(
        f"💸 Digite o valor para REMOVER do saldo do usuário {target_user_id}:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin_user_detail_{target_user_id}")]
        ])
    )
    
    return USER_EDIT_STATE


async def admin_process_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa adição/remoção de saldo"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    try:
        amount = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Digite um número.")
        return USER_EDIT_STATE
    
    target_user_id = context.user_data.get('admin_target_user')
    action = context.user_data.get('admin_action')
    
    if not target_user_id or not action:
        await update.message.reply_text("❌ Erro. Tente novamente.")
        return ConversationHandler.END
    
    user_service = UserService()
    
    if action == 'add_balance':
        result = await user_service.add_balance(target_user_id, amount, admin_id)
        action_text = "adicionado"
    else:
        result = await user_service.remove_balance(target_user_id, amount, admin_id)
        action_text = "removido"
    
    if result['success']:
        message = (
            f"✅ Saldo {action_text} com sucesso!\n\n"
            f"👤 Usuário: {target_user_id}\n"
            f"💰 Valor: R$ {amount:.2f}\n"
            f"💳 Novo saldo: R$ {result['new_balance']:.2f}"
        )
    else:
        message = f"❌ Erro: {result.get('error', 'Erro desconhecido')}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Ver Usuário", callback_data=f"admin_user_detail_{target_user_id}")],
        [InlineKeyboardButton("⬅️ Voltar à Lista", callback_data="admin_users_list")],
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard)
    
    return ConversationHandler.END


async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bloqueia/desbloqueia um usuário"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    data = query.data
    
    if "admin_block_user_" in data:
        target_id = int(data.replace("admin_block_user_", ""))
        action = "block"
    elif "admin_unblock_user_" in data:
        target_id = int(data.replace("admin_unblock_user_", ""))
        action = "unblock"
    else:
        return ConversationHandler.END
    
    user_service = UserService()
    
    if action == "block":
        result = await user_service.block_user(target_id, admin_id)
        msg = "bloqueado"
    else:
        result = await user_service.unblock_user(target_id, admin_id)
        msg = "desbloqueado"
    
    if result['success']:
        message = f"✅ Usuário {target_id} {msg} com sucesso!"
    else:
        message = f"❌ Erro ao {msg} usuário."
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin_user_detail_{target_id}")]
        ])
    )
    
    return ConversationHandler.END
