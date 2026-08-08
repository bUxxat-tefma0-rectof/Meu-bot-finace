"""
Handler de Administradores (Admin)
Gerencia outros administradores e permissões
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from database.repositories.user_repository import UserRepository
from admin.keyboards.admin_menu import get_admin_back_button

logger = logging.getLogger(__name__)

ADMIN_MANAGE_STATE = 1


async def admin_manage_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista administradores"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    # Lista admins cadastrados
    admin_ids = settings.ADMIN_IDS
    
    message = (
        f"🔐 GERENCIAR ADMINISTRADORES\n\n"
        f"👑 Administradores cadastrados:\n\n"
    )
    
    for aid in admin_ids:
        is_owner = "👑" if aid == admin_ids[0] else "🛠️"
        message += f"{is_owner} ID: {aid}\n"
    
    message += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Para adicionar um novo admin, use:\n"
        f"/add_admin <telegram_id>\n\n"
        f"📌 Para remover um admin, use:\n"
        f"/remove_admin <telegram_id>\n\n"
        f"⚠️ Apenas o Dono (👑) pode gerenciar admins."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Adicionar Admin", callback_data="admin_add_new"),
            InlineKeyboardButton("➖ Remover Admin", callback_data="admin_remove"),
        ],
        [InlineKeyboardButton("📋 Ver Permissões", callback_data="admin_permissions")],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_MANAGE_STATE


async def admin_add_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona novo administrador"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    await query.edit_message_text(
        "➕ ADICIONAR ADMINISTRADOR\n\n"
        "Digite o ID do Telegram do novo admin:\n\n"
        "Exemplo: 123456789\n\n"
        "Use /cancel para cancelar.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_manage_list")],
        ])
    )
    
    context.user_data['admin_action'] = 'add_admin'
    
    return ADMIN_MANAGE_STATE


async def admin_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove administrador"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    await query.edit_message_text(
        "➖ REMOVER ADMINISTRADOR\n\n"
        "Digite o ID do Telegram do admin a remover:\n\n"
        "Use /cancel para cancelar.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_manage_list")],
        ])
    )
    
    context.user_data['admin_action'] = 'remove_admin'
    
    return ADMIN_MANAGE_STATE


async def admin_process_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa adição/remoção de admin"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    action = context.user_data.get('admin_action')
    text = update.message.text.strip()
    
    try:
        target_id = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ ID inválido. Digite apenas números.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_manage_list")],
            ])
        )
        return ADMIN_MANAGE_STATE
    
    if target_id == admin_id:
        await update.message.reply_text(
            "❌ Você não pode gerenciar a si mesmo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_manage_list")],
            ])
        )
        return ADMIN_MANAGE_STATE
    
    if action == 'add_admin':
        if target_id in settings.ADMIN_IDS:
            message = f"❌ ID {target_id} já é administrador."
        else:
            settings.ADMIN_IDS.append(target_id)
            message = f"✅ Administrador {target_id} adicionado com sucesso!"
            
            # Torna o usuário admin no banco
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(target_id)
            if user:
                await user_repo.update(user.id, is_admin=True)
    
    elif action == 'remove_admin':
        if target_id not in settings.ADMIN_IDS:
            message = f"❌ ID {target_id} não é administrador."
        elif len(settings.ADMIN_IDS) <= 1:
            message = "❌ Não é possível remover o último administrador."
        else:
            settings.ADMIN_IDS.remove(target_id)
            message = f"✅ Administrador {target_id} removido com sucesso!"
            
            # Remove admin do banco
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(target_id)
            if user:
                await user_repo.update(user.id, is_admin=False)
    
    else:
        message = "❌ Ação inválida."
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Ver Lista", callback_data="admin_manage_list")],
        ])
    )
    
    context.user_data.pop('admin_action', None)
    
    return ConversationHandler.END


async def admin_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra permissões"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    message = (
        f"📋 PERMISSÕES DE ADMINISTRADORES\n\n"
        f"👑 Dono: Acesso total\n"
        f"🛠️ Gerente: Produtos, estoque, usuários\n"
        f"💰 Financeiro: Pagamentos e saldo\n"
        f"📦 Estoque: Somente estoque\n\n"
        f"Sistema de permissões granulares em desenvolvimento."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_manage_list")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return ADMIN_MANAGE_STATE
