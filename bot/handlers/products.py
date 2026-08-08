"""
Handler de Produtos
Visualização e compra de produtos
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.products import ProductService
from services.orders import OrderService
from services.users import UserService
from services.inventory import InventoryService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

PRODUCT_STATE = 1


async def product_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra detalhes de um produto"""
    query = update.callback_query
    await query.answer()
    
    # Verifica se é volta para catálogo
    if query.data == "back_to_catalog":
        from bot.handlers.catalog import catalog_command
        return await catalog_command(update, context)
    
    product_id = int(query.data.replace("product_", ""))
    
    # Busca dados do produto
    product_service = ProductService()
    product = await product_service.get_product(product_id)
    
    if not product:
        await query.edit_message_text(
            "❌ Produto não encontrado.",
            reply_markup=InlineKeyboardMarkup([[get_back_button()]])
        )
        return ConversationHandler.END
    
    # Registra visualização
    await product_service.increment_views(product_id, update.effective_user.id)
    
    # Dados do usuário
    user_service = UserService()
    user_data = await user_service.get_user(update.effective_user.id)
    balance = user_data.get('balance', 0)
    
    # Informações do produto
    name = product.get('name', 'Produto')
    price = product.get('price', 0)
    stock = product.get('stock_count', 0)
    description = product.get('description', '')
    warranty = product.get('warranty', '7 dias')
    sales = product.get('total_sales', 0)
    views = product.get('active_viewers', 0)
    image_id = product.get('image_id')
    
    # Mensagem do produto
    product_message = (
        f"🔥 {name}\n"
        f"{'🟢 DISPONÍVEL' if stock > 0 else '🔴 INDISPONÍVEL'}\n\n"
        f"├ 💵 Preço: R$ {price:.2f}\n"
        f"├ 💰 Seu Saldo: R$ {balance:.2f}\n"
        f"└ 📦 Estoque: {stock} unidades\n\n"
    )
    
    if description:
        product_message += f"📝 Descrição:\n{description}\n\n"
    
    product_message += (
        f"📊 Estatísticas:\n"
        f"⚡️ Já foram vendidas {sales} unidades!\n"
        f"👀 {views} pessoas visualizando agora\n"
        f"🛡 Garantia: {warranty}\n"
        f"✅ Compra segura."
    )
    
    # Botões de ação
    keyboard_buttons = []
    
    if stock > 0 and balance >= price:
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"🛒 COMPRAR - R$ {price:.2f}",
                callback_data=f"confirm_purchase_{product_id}"
            )
        ])
    elif stock > 0 and balance < price:
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"💳 ADICIONAR SALDO (Precisa R$ {price - balance:.2f})",
                callback_data="go_to_wallet"
            )
        ])
    elif stock == 0:
        keyboard_buttons.append([
            InlineKeyboardButton("📭 AVISAR QUANDO DISPONÍVEL", callback_data=f"notify_stock_{product_id}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_category"),
        InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    # Envia imagem do produto se existir
    if image_id:
        try:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_id,
                caption=product_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {e}")
            await query.edit_message_text(
                product_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    else:
        await query.edit_message_text(
            product_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    # Armazena produto atual no contexto
    context.user_data['current_product'] = product
    
    return PRODUCT_STATE


async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia processo de compra"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.replace("buy_product_", ""))
    
    # Redireciona para confirmação
    return await confirm_purchase(update, context, product_id)


async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id=None):
    """Confirma e processa a compra"""
    query = update.callback_query
    
    if not product_id:
        callback_data = query.data
        if callback_data.startswith("confirm_purchase_"):
            product_id = int(callback_data.replace("confirm_purchase_", ""))
        else:
            await query.edit_message_text("❌ Erro ao processar compra.")
            return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    # Processa a compra
    order_service = OrderService()
    result = await order_service.process_purchase(user_id, product_id)
    
    if not result['success']:
        error_msg = result.get('error', 'Erro desconhecido')
        
        if result.get('error_type') == 'insufficient_balance':
            message = settings.INSUFFICIENT_BALANCE.format(
                preco=f"{result['price']:.2f}",
                saldo=f"{result['balance']:.2f}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Adicionar Saldo", callback_data="go_to_wallet")],
                [get_back_button()]
            ])
        else:
            message = f"❌ {error_msg}"
            keyboard = InlineKeyboardMarkup([[get_back_button()]])
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return PRODUCT_STATE
    
    # Compra realizada com sucesso
    purchase_data = result['purchase']
    
    success_message = settings.PURCHASE_SUCCESS.format(
        produto=purchase_data['product_name'],
        preco=f"{purchase_data['price']:.2f}",
        saldo=f"{result['new_balance']:.2f}",
        conteudo_entrega=purchase_data['delivery_content']
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar Mais", callback_data="back_to_catalog")],
        [InlineKeyboardButton("📜 Ver Histórico", callback_data="btn_history")],
        [get_back_button()]
    ])
    
    await query.edit_message_text(
        success_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Notifica canal
    from services.notifications import NotificationService
    notification_service = NotificationService()
    await notification_service.notify_purchase(user_id, purchase_data, context)
    
    return ConversationHandler.END
