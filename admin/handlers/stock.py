"""
Handler de Gerenciamento de Estoque (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.inventory import InventoryService
from services.products import ProductService

logger = logging.getLogger(__name__)

STOCK_LIST_STATE = 1
STOCK_ADD_STATE = 2


async def admin_stock_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia estoque de produtos"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    inventory_service = InventoryService()
    product_service = ProductService()
    
    products = await product_service.get_all_products_admin()
    
    message = "📦 GERENCIAR ESTOQUE\n\n"
    
    for product in products:
        stock_count = product.get('stock_count', 0)
        status = "🟢" if stock_count > 0 else "🔴"
        message += (
            f"{status} {product['name']}\n"
            f"   📦 Estoque: {stock_count}\n"
            f"   🛒 Vendas: {product.get('total_sales', 0)}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar Estoque", callback_data="admin_stock_add_select")],
        [InlineKeyboardButton("📥 Importar em Massa", callback_data="admin_stock_import")],
        [InlineKeyboardButton("📊 Ver Disponíveis", callback_data="admin_stock_available")],
        [InlineKeyboardButton("✅ Ver Vendidos", callback_data="admin_stock_sold")],
        [InlineKeyboardButton("📋 Exportar Histórico", callback_data="admin_stock_export")],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return STOCK_LIST_STATE


async def admin_stock_add_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona produto para adicionar estoque"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    product_service = ProductService()
    products = await product_service.get_all_products_admin()
    
    keyboard_buttons = []
    for product in products:
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"📦 {product['name']} ({product.get('stock_count', 0)} unid.)",
                callback_data=f"admin_stock_add_{product['id']}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")
    ])
    
    await query.edit_message_text(
        "📦 Selecione o produto para adicionar estoque:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )
    
    return STOCK_ADD_STATE


async def admin_stock_add_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe itens para adicionar ao estoque"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    product_id = int(query.data.replace("admin_stock_add_", ""))
    context.user_data['admin_stock_product_id'] = product_id
    
    product_service = ProductService()
    product = await product_service.get_product(product_id)
    
    if not product:
        await query.edit_message_text(
            "❌ Produto não encontrado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")]
            ])
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"📦 ADICIONAR ESTOQUE\n\n"
        f"Produto: {product['name']}\n"
        f"Estoque atual: {product.get('stock_count', 0)}\n\n"
        f"Envie os itens (um por linha):\n\n"
        f"Exemplo:\n"
        f"codigo123\n"
        f"codigo456\n"
        f"codigo789\n\n"
        f"Você pode colar vários de uma vez!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_stock_manage")]
        ])
    )
    
    return STOCK_ADD_STATE


async def admin_stock_process_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa itens enviados para estoque"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    product_id = context.user_data.get('admin_stock_product_id')
    
    if not product_id:
        await update.message.reply_text("❌ Erro. Selecione um produto primeiro.")
        return ConversationHandler.END
    
    # Processa itens (um por linha)
    text = update.message.text
    items = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not items:
        await update.message.reply_text("❌ Nenhum item enviado. Tente novamente.")
        return STOCK_ADD_STATE
    
    inventory_service = InventoryService()
    result = await inventory_service.add_items(product_id, items, admin_id)
    
    if result['success']:
        message = (
            f"✅ Estoque adicionado com sucesso!\n\n"
            f"📦 Itens adicionados: {result['items_added']}\n"
            f"📊 Estoque total: {result['total_stock']}\n"
        )
        
        if result.get('duplicates', 0) > 0:
            message += f"⚠️ Itens duplicados ignorados: {result['duplicates']}"
    else:
        message = f"❌ Erro: {result.get('error')}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar Mais", callback_data=f"admin_stock_add_{product_id}")],
        [InlineKeyboardButton("📦 Ver Estoque", callback_data="admin_stock_manage")],
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard)
    
    # Limpa dados temporários
    context.user_data.pop('admin_stock_product_id', None)
    
    return ConversationHandler.END


async def admin_stock_available(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra itens disponíveis no estoque"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    inventory_service = InventoryService()
    
    # Pede para selecionar produto
    product_service = ProductService()
    products = await product_service.get_all_products_admin()
    
    keyboard_buttons = []
    for product in products:
        if product.get('stock_count', 0) > 0:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"{product['name']} ({product['stock_count']} unid.)",
                    callback_data=f"admin_view_stock_{product['id']}"
                )
            ])
    
    if not keyboard_buttons:
        await query.edit_message_text(
            "📭 Nenhum produto com estoque disponível.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")]
            ])
        )
        return STOCK_LIST_STATE
    
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")
    ])
    
    await query.edit_message_text(
        "📦 Selecione o produto para ver itens disponíveis:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )
    
    return STOCK_LIST_STATE


async def admin_stock_view_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Visualiza itens do estoque"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    product_id = int(query.data.replace("admin_view_stock_", ""))
    
    inventory_service = InventoryService()
    items = await inventory_service.get_available_items(product_id)
    
    product_service = ProductService()
    product = await product_service.get_product(product_id)
    
    if not items:
        message = f"📦 {product['name'] if product else 'Produto'}\n\n📭 Nenhum item disponível."
    else:
        message = (
            f"📦 {product['name'] if product else 'Produto'}\n"
            f"📊 Itens disponíveis: {len(items)}\n\n"
        )
        
        for i, item in enumerate(items[:50], 1):
            message += f"{i}. <code>{item['code']}</code>\n"
        
        if len(items) > 50:
            message += f"\n... e mais {len(items) - 50} itens."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Remover Itens", callback_data=f"admin_remove_stock_{product_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")],
    ])
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return STOCK_LIST_STATE


async def admin_stock_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporta histórico de estoque"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    inventory_service = InventoryService()
    history = await inventory_service.get_stock_history()
    
    if not history:
        message = "📭 Nenhum histórico de estoque."
    else:
        message = "📊 HISTÓRICO DE ESTOQUE\n\n"
        
        for entry in history[:20]:
            message += (
                f"📅 {entry['date']}\n"
                f"📦 {entry['product_name']}\n"
                f"➕ Adicionados: {entry['items_added']}\n"
                f"👤 Por: {entry.get('admin_name', 'Sistema')}\n\n"
            )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Exportar CSV", callback_data="admin_export_csv")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_stock_manage")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard)
    
    return STOCK_LIST_STATE
