"""
Teclados do menu principal e utilitários
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.products import ProductService


async def get_main_menu_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """
    Retorna o teclado do menu principal
    Pode ser customizado via banco de dados
    """
    
    # Busca botões customizados do banco (se existirem)
    # Por enquanto usa os botões padrão
    buttons = [
        [InlineKeyboardButton("🛒 Comprar Gift Card", callback_data="btn_buy_giftcard")],
        [InlineKeyboardButton("👤 Meu Perfil", callback_data="btn_my_profile")],
        [InlineKeyboardButton("💳 Adicionar Saldo", callback_data="btn_add_balance")],
        [InlineKeyboardButton("📜 Histórico", callback_data="btn_history")],
        [InlineKeyboardButton("🤝 Afiliados", callback_data="btn_affiliates")],
        [InlineKeyboardButton("💬 Suporte", callback_data="btn_support")],
    ]
    
    return InlineKeyboardMarkup(buttons)


def get_back_button(callback_data: str = "menu_main") -> InlineKeyboardButton:
    """Retorna botão de voltar padrão"""
    return InlineKeyboardButton("⬅️ Voltar", callback_data=callback_data)


def get_cancel_button(callback_data: str = "menu_main") -> InlineKeyboardButton:
    """Retorna botão de cancelar"""
    return InlineKeyboardButton("❌ Cancelar", callback_data=callback_data)
