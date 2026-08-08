"""
Handler de Configurações do Sistema (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.messages import MessageService

logger = logging.getLogger(__name__)

SETTINGS_MAIN_STATE = 1
SETTINGS_EDIT_STATE = 2


async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de configurações do sistema"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    message = (
        f"⚙️ CONFIGURAÇÕES DO SISTEMA\n\n"
        f"Escolha uma seção para configurar:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pagamentos PIX", callback_data="admin_settings_pix")],
        [InlineKeyboardButton("🤝 Afiliados", callback_data="admin_settings_affiliates")],
        [InlineKeyboardButton("📢 Canal Obrigatório", callback_data="admin_settings_channel")],
        [InlineKeyboardButton("🔔 Notificações", callback_data="admin_settings_notifications")],
        [InlineKeyboardButton("📝 Mensagens", callback_data="admin_settings_messages")],
        [InlineKeyboardButton("🎨 Aparência do Bot", callback_data="admin_settings_appearance")],
        [InlineKeyboardButton("💬 Suporte", callback_data="admin_settings_support")],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return SETTINGS_MAIN_STATE


async def admin_settings_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configurações do PIX"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    pix_config = settings.get_payment_config()
    
    message = (
        f"💳 CONFIGURAÇÕES PIX\n\n"
        f"Provedor: {pix_config['provider']}\n"
        f"Ambiente: {pix_config['environment']}\n"
        f"URL API: {pix_config['api_url'][:50]}...\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Mínimo: R$ {pix_config['min_value']:.2f}\n"
        f"💰 Máximo: R$ {pix_config['max_value']:.2f}\n"
        f"⏳ Expiração: {pix_config['expiration_minutes']} min\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {'🟢 Ativo' if pix_config.get('active', True) else '🔴 Inativo'}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Alterar Provedor", callback_data="admin_edit_pix_provider")],
        [InlineKeyboardButton("🔑 Editar Credenciais", callback_data="admin_edit_pix_credentials")],
        [InlineKeyboardButton("💰 Alterar Limites", callback_data="admin_edit_pix_limits")],
        [InlineKeyboardButton("🔗 Testar Conexão", callback_data="admin_test_pix_connection")],
        [InlineKeyboardButton("🟢 Ativar/Desativar", callback_data="admin_toggle_pix")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_settings")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return SETTINGS_EDIT_STATE


async def admin_settings_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Editor de mensagens do bot"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    message_types = [
        ("Boas-vindas", "welcome"),
        ("Acesso Bloqueado", "blocked"),
        ("Menu Principal", "menu"),
        ("Catálogo", "catalog"),
        ("Produto", "product"),
        ("Saldo Insuficiente", "insufficient_balance"),
        ("PIX Gerado", "pix_generated"),
        ("PIX Aprovado", "pix_approved"),
        ("PIX Expirado", "pix_expired"),
        ("Compra Realizada", "purchase_success"),
        ("Perfil", "profile"),
        ("Histórico", "history"),
        ("Afiliados", "affiliate"),
        ("Suporte", "support"),
    ]
    
    keyboard_buttons = []
    for name, key in message_types:
        keyboard_buttons.append([
            InlineKeyboardButton(f"📝 {name}", callback_data=f"admin_edit_message_{key}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="admin_settings")
    ])
    
    await query.edit_message_text(
        "📝 EDITOR DE MENSAGENS\n\nSelecione a mensagem para editar:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )
    
    return SETTINGS_EDIT_STATE


async def admin_settings_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edita uma mensagem específica"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    message_key = query.data.replace("admin_edit_message_", "")
    context.user_data['admin_edit_message_key'] = message_key
    
    message_service = MessageService()
    current_message = await message_service.get_message(message_key)
    
    await query.edit_message_text(
        f"📝 EDITAR MENSAGEM: {message_key}\n\n"
        f"Mensagem atual:\n\n"
        f"{current_message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Envie a nova mensagem:\n\n"
        f"Variáveis disponíveis:\n"
        f"{{nome}}, {{username}}, {{telegram_id}}, {{saldo}},\n"
        f"{{compras}}, {{total_gasto}}, {{produto}}, {{preco}},\n"
        f"{{estoque}}, {{vendas}}, {{categoria}}, {{garantia}},\n"
        f"{{data}}, {{hora}}, {{pix_valor}}, {{pix_expiracao}},\n"
        f"{{comissao}}, {{link_afiliado}}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_settings_messages")]
        ]),
        parse_mode=ParseMode.HTML
    )
    
    return SETTINGS_EDIT_STATE


async def admin_settings_save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva a mensagem editada"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    message_key = context.user_data.get('admin_edit_message_key')
    new_message = update.message.text
    
    if not message_key:
        return ConversationHandler.END
    
    message_service = MessageService()
    result = await message_service.update_message(message_key, new_message, admin_id)
    
    if result['success']:
        await update.message.reply_text(
            "✅ Mensagem atualizada com sucesso!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Editar Outra", callback_data="admin_settings_messages")],
                [InlineKeyboardButton("⬅️ Configurações", callback_data="admin_settings")],
            ])
        )
    else:
        await update.message.reply_text(
            f"❌ Erro ao salvar: {result.get('error')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_settings_messages")]
            ])
        )
    
    context.user_data.pop('admin_edit_message_key', None)
    
    return ConversationHandler.END


async def admin_test_pix_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Testa conexão com API PIX"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer("Testando conexão...")
    
    from payments.pix import PixPaymentService
    
    pix_service = PixPaymentService()
    result = await pix_service.test_connection()
    
    if result['success']:
        await query.edit_message_text(
            "✅ Conexão com a API PIX estabelecida com sucesso!\n\n"
            f"Provedor: {settings.PIX_PROVIDER}\n"
            f"Ambiente: {settings.PIX_ENVIRONMENT}\n"
            f"Resposta: {result.get('message', 'OK')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_settings_pix")]
            ])
        )
    else:
        await query.edit_message_text(
            f"❌ Falha na conexão!\n\n"
            f"Erro: {result.get('error', 'Erro desconhecido')}\n\n"
            f"Verifique suas credenciais.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Editar Credenciais", callback_data="admin_edit_pix_credentials")],
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_settings_pix")],
            ])
        )
    
    return SETTINGS_EDIT_STATE
