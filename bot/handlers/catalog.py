"""
Handler do Catálogo de Categorias
Mostra categorias e redireciona para produtos
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from services.products import ProductService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

CATALOG_STATE = 1


async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o catálogo de categorias"""
    query = update.callback_query
    
    # Busca categorias ativas
    product_service = ProductService()
    categories = await product_service.get_active_categories()
    
    if not categories:
        message = "📭 Nenhuma categoria disponível no momento."
        keyboard = InlineKeyboardMarkup([[get_back_button()]])
        
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(message, reply_markup=keyboard)
        
        return CATALOG_STATE
    
    # Monta teclado com categorias
    keyboard_buttons = []
    for category in categories:
        emoji = category.get('emoji', '📦')
        name = category.get('name', 'Categoria')
        cat_id = category.get('id')
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"{emoji} {name}",
                callback_data=f"category_{cat_id}"
            )
        ])
    
    # Adiciona botão voltar
    keyboard_buttons.append([get_back_button()])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    # Mensagem do catálogo
    message = settings.CATALOG_MESSAGE
    
    if query:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    return CATALOG_STATE


async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa seleção de categoria e mostra produtos"""
    query = update.callback_query
    await query.answer()
    
    category_id = int(query.data.replace("category_", ""))
    
    # Busca produtos da categoria
    product_service = ProductService()
    products = await product_service.get_products_by_category(category_id)
    
    if not products:
        await query.edit_message_text(
            "📭 Nenhum produto disponível nesta categoria.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_catalog")],
                [get_back_button()]
            ])
        )
        return CATALOG_STATE
    
    # Monta lista de produtos
    keyboard_buttons = []
    for product in products:
        name = product.get('name', 'Produto')
        price = product.get('price', 0)
        stock = product.get('stock', 0)
        prod_id = product.get('id')
        
        # Status do estoque
        if stock > 0:
            status = "🟢"
            stock_text = f"{stock} unid."
        else:
            status = "🔴"
            stock_text = "Esgotado"
        
        button_text = f"{status} {name} - R$ {price:.2f}"
        keyboard_buttons.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"product_{prod_id}"
            )
        ])
    
    # Botões de navegação
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar para Categorias", callback_data="back_to_catalog")
    ])
    keyboard_buttons.append([get_back_button()])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    # Busca nome da categoria
    category = await product_service.get_category(category_id)
    category_name = category.get('name', 'Categoria') if category else 'Categoria'
    
    message = f"🛒 {category_name}\n\n📦 {len(products)} produtos disponíveis\nSelecione um produto:"
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return CATALOG_STATE
