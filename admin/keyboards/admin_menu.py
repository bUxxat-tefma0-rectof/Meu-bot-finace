"""
Teclados do painel administrativo
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Teclado principal do painel admin"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👥 Usuários", callback_data="admin_users")],
        [InlineKeyboardButton("🛒 Produtos", callback_data="admin_products")],
        [InlineKeyboardButton("📦 Estoque", callback_data="admin_stock")],
        [InlineKeyboardButton("💳 Pagamentos", callback_data="admin_payments")],
        [InlineKeyboardButton("🤝 Afiliados", callback_data="admin_affiliates")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data="admin_settings")],
        [InlineKeyboardButton("📋 Logs", callback_data="admin_logs")],
    ])


def get_back_to_dashboard_button() -> InlineKeyboardButton:
    """Botão de voltar ao dashboard"""
    return InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")


def get_admin_back_button(callback_data: str = "admin_dashboard") -> InlineKeyboardButton:
    """Botão de voltar genérico do admin"""
    return InlineKeyboardButton("⬅️ Voltar", callback_data=callback_data)
