"""
Handler do Histórico de Compras
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from services.orders import OrderService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

HISTORY_STATE = 1
ITEMS_PER_PAGE = 5


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o histórico de compras"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Parâmetros de paginação
    page = context.user_data.get('history_page', 1)
    
    # Busca compras
    order_service = OrderService()
    result = await order_service.get_user_orders(user_id, page=page, per_page=ITEMS_PER_PAGE)
    
    orders = result['orders']
    total_orders = result['total']
    total_pages = result['total_pages']
    
    if not orders:
        message = "📭 Você ainda não fez nenhuma compra."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Comprar Gift Cards", callback_data="btn_buy_giftcard")],
            [get_back_button()]
        ])
    else:
        message = f"📜 Histórico de Compras\n\n"
        
        for i, order in enumerate(orders, 1):
            order_num = (page - 1) * ITEMS_PER_PAGE + i
            message += (
                f"{order_num}. 🛒 {order['product_name']}\n"
                f"   💰 R$ {order['price']:.2f}\n"
                f"   📅 {order['purchase_date']}\n"
                f"   ⏰ {order['purchase_time']}\n"
                f"   ✅ Concluída\n\n"
            )
        
        message += f"📄 Página {page} de {total_pages}"
        
        # Botões de navegação
        keyboard_buttons = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Anterior", callback_data=f"history_page_{page - 1}")
            )
        
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton("Próxima ➡️", callback_data=f"history_page_{page + 1}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        # Botão para ver detalhes
        for i, order in enumerate(orders):
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"🔍 Detalhes: {order['product_name']}",
                    callback_data=f"history_detail_{order['id']}"
                )
            ])
        
        keyboard_buttons.append([get_back_button()])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    if query:
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    return HISTORY_STATE


async def history_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra detalhes de uma compra específica"""
    query = update.callback_query
    await query.answer()
    
    # Verifica se é navegação de página
    if query.data.startswith("history_page_"):
        page = int(query.data.replace("history_page_", ""))
        context.user_data['history_page'] = page
        return await history_command(update, context)
    
    order_id = int(query.data.replace("history_detail_", ""))
    
    # Busca detalhes da compra
    order_service = OrderService()
    order = await order_service.get_order_detail(order_id)
    
    if not order:
        await query.edit_message_text(
            "❌ Compra não encontrada.",
            reply_markup=InlineKeyboardMarkup([[get_back_button()]])
        )
        return HISTORY_STATE
    
    detail_message = (
        f"📦 Detalhes da Compra\n\n"
        f"🆔 Pedido: #{order['id']}\n"
        f"🎁 Produto: {order['product_name']}\n"
        f"💰 Valor: R$ {order['price']:.2f}\n"
        f"📅 Data: {order['purchase_date']}\n"
        f"⏰ Hora: {order['purchase_time']}\n"
        f"💳 Método: {order['payment_method']}\n"
        f"✅ Status: {order['status']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📦 Conteúdo:\n"
        f"<code>{order['delivery_content']}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🛡 Garantia: {order['warranty']}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copiar Conteúdo", callback_data=f"copy_content_{order['id']}")],
        [InlineKeyboardButton("⬅️ Voltar ao Histórico", callback_data="history_back")],
        [get_back_button()]
    ])
    
    await query.edit_message_text(
        detail_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return HISTORY_STATE
