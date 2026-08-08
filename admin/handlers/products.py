"""
Handler de Gerenciamento de Produtos (Admin)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.products import ProductService

logger = logging.getLogger(__name__)

PRODUCTS_LIST_STATE = 1
PRODUCT_EDIT_STATE = 2
PRODUCT_CREATE_STATE = 3


async def admin_products_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os produtos"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    product_service = ProductService()
    products = await product_service.get_all_products_admin()
    
    if not products:
        message = "📭 Nenhum produto cadastrado."
    else:
        message = f"🛒 PRODUTOS ({len(products)})\n\n"
        
        for i, product in enumerate(products, 1):
            status = "🟢" if product.get('is_active') else "🔴"
            stock_status = "📦" if product.get('stock_count', 0) > 0 else "❌"
            
            message += (
                f"{i}. {status} {stock_status} {product.get('name', 'N/A')}\n"
                f"   💵 R$ {product.get('price', 0):.2f}\n"
                f"   📦 Estoque: {product.get('stock_count', 0)}\n"
                f"   🛒 Vendas: {product.get('total_sales', 0)}\n\n"
            )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Novo Produto", callback_data="admin_product_create")],
        [InlineKeyboardButton("📋 Editar Produto", callback_data="admin_product_edit_select")],
        [InlineKeyboardButton("🗑️ Excluir Produto", callback_data="admin_product_delete")],
        [InlineKeyboardButton("📦 Gerenciar Estoque", callback_data="admin_stock_manage")],
        [InlineKeyboardButton("📊 Ver Categorias", callback_data="admin_categories")],
        [InlineKeyboardButton("⬅️ Voltar ao Dashboard", callback_data="admin_back_to_dashboard")],
    ])
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    return PRODUCTS_LIST_STATE


async def admin_product_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia criação de novo produto"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    context.user_data['admin_product_step'] = 1
    context.user_data['admin_new_product'] = {}
    
    await query.edit_message_text(
        "➕ NOVO PRODUTO\n\n"
        "Etapa 1/8 - Nome do Produto\n\n"
        "Digite o nome do produto:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_products_list")]
        ])
    )
    
    return PRODUCT_CREATE_STATE


async def admin_product_create_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa etapas de criação de produto"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    step = context.user_data.get('admin_product_step', 1)
    product_data = context.user_data.get('admin_new_product', {})
    text = update.message.text
    
    if step == 1:  # Nome
        product_data['name'] = text
        await update.message.reply_text(
            "Etapa 2/8 - Categoria\n\n"
            "Digite o nome da categoria:"
        )
    
    elif step == 2:  # Categoria
        product_data['category'] = text
        await update.message.reply_text(
            "Etapa 3/8 - Preço\n\n"
            "Digite o preço (apenas números):"
        )
    
    elif step == 3:  # Preço
        try:
            product_data['price'] = float(text.replace(",", "."))
            await update.message.reply_text(
                "Etapa 4/8 - Descrição\n\n"
                "Digite a descrição do produto:"
            )
        except ValueError:
            await update.message.reply_text("❌ Preço inválido. Digite um número.")
            return PRODUCT_CREATE_STATE
    
    elif step == 4:  # Descrição
        product_data['description'] = text
        await update.message.reply_text(
            "Etapa 5/8 - Garantia\n\n"
            "Digite a garantia (ex: 7 dias):"
        )
    
    elif step == 5:  # Garantia
        product_data['warranty'] = text
        await update.message.reply_text(
            "Etapa 6/8 - Texto de Entrega\n\n"
            "Digite o texto que aparece na entrega do produto.\n"
            "Use {codigo} onde o gift card será inserido."
        )
    
    elif step == 6:  # Texto de entrega
        product_data['delivery_text'] = text
        await update.message.reply_text(
            "Etapa 7/8 - Tipo de Entrega\n\n"
            "Digite:\n"
            "1 - Texto único\n"
            "2 - Código individual do estoque"
        )
    
    elif step == 7:  # Tipo de entrega
        try:
            delivery_type = int(text)
            if delivery_type in [1, 2]:
                product_data['delivery_type'] = delivery_type
                
                # Salva o produto
                product_service = ProductService()
                result = await product_service.create_product(product_data, admin_id)
                
                if result['success']:
                    message = (
                        f"✅ Produto criado com sucesso!\n\n"
                        f"📦 {product_data['name']}\n"
                        f"💰 R$ {product_data['price']:.2f}\n"
                        f"📂 Categoria: {product_data['category']}\n\n"
                        f"Deseja adicionar estoque agora?"
                    )
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📦 Adicionar Estoque", callback_data=f"admin_stock_add_{result['product_id']}")],
                        [InlineKeyboardButton("📋 Ver Produtos", callback_data="admin_products_list")],
                    ])
                    
                    await update.message.reply_text(message, reply_markup=keyboard)
                    
                    # Limpa dados temporários
                    context.user_data.pop('admin_product_step', None)
                    context.user_data.pop('admin_new_product', None)
                    
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        f"❌ Erro ao criar produto: {result.get('error')}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_products_list")]
                        ])
                    )
                    return ConversationHandler.END
            else:
                await update.message.reply_text("❌ Digite 1 ou 2.")
                return PRODUCT_CREATE_STATE
        except ValueError:
            await update.message.reply_text("❌ Digite 1 ou 2.")
            return PRODUCT_CREATE_STATE
    
    # Próximo passo
    context.user_data['admin_product_step'] = step + 1
    context.user_data['admin_new_product'] = product_data
    
    return PRODUCT_CREATE_STATE


async def admin_product_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edita um produto existente"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        await query.answer("Acesso negado!", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    if query.data == "admin_product_edit_select":
        product_service = ProductService()
        products = await product_service.get_all_products_admin()
        
        keyboard_buttons = []
        for product in products:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"{product['name']} - R$ {product['price']:.2f}",
                    callback_data=f"admin_edit_product_{product['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("⬅️ Voltar", callback_data="admin_products_list")
        ])
        
        await query.edit_message_text(
            "📋 Selecione o produto para editar:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
        
        return PRODUCT_EDIT_STATE
    
    elif query.data.startswith("admin_edit_product_"):
        product_id = int(query.data.replace("admin_edit_product_", ""))
        context.user_data['admin_edit_product_id'] = product_id
        
        # Mostra opções de edição
        product_service = ProductService()
        product = await product_service.get_product(product_id)
        
        if not product:
            await query.edit_message_text(
                "❌ Produto não encontrado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_products_list")]
                ])
            )
            return ConversationHandler.END
        
        message = (
            f"📝 EDITAR PRODUTO\n\n"
            f"📦 {product['name']}\n"
            f"💰 R$ {product['price']:.2f}\n"
            f"📂 Categoria: {product.get('category_name', 'N/A')}\n"
            f"📦 Estoque: {product.get('stock_count', 0)}\n\n"
            f"Selecione o que deseja editar:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Nome", callback_data=f"admin_edit_field_name_{product_id}")],
            [InlineKeyboardButton("💰 Preço", callback_data=f"admin_edit_field_price_{product_id}")],
            [InlineKeyboardButton("📂 Categoria", callback_data=f"admin_edit_field_category_{product_id}")],
            [InlineKeyboardButton("📝 Descrição", callback_data=f"admin_edit_field_description_{product_id}")],
            [InlineKeyboardButton("🛡 Garantia", callback_data=f"admin_edit_field_warranty_{product_id}")],
            [InlineKeyboardButton("🖼️ Imagem", callback_data=f"admin_edit_field_image_{product_id}")],
            [InlineKeyboardButton("🟢 Ativar/Desativar", callback_data=f"admin_toggle_product_{product_id}")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_products_list")],
        ])
        
        await query.edit_message_text(message, reply_markup=keyboard)
        
        return PRODUCT_EDIT_STATE
    
    return PRODUCTS_LIST_STATE


async def admin_product_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa edição de campo específico"""
    query = update.callback_query
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    await query.answer()
    
    data = query.data
    
    if data.startswith("admin_edit_field_"):
        parts = data.replace("admin_edit_field_", "").split("_")
        field = parts[0]
        product_id = int(parts[-1])
        
        context.user_data['admin_edit_field'] = field
        context.user_data['admin_edit_product_id'] = product_id
        
        field_names = {
            'name': 'nome',
            'price': 'preço',
            'category': 'categoria',
            'description': 'descrição',
            'warranty': 'garantia',
            'image': 'imagem',
        }
        
        field_name = field_names.get(field, field)
        
        if field == 'image':
            await query.edit_message_text(
                f"🖼️ Envie a nova imagem para o produto:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin_edit_product_{product_id}")]
                ])
            )
        else:
            await query.edit_message_text(
                f"📝 Digite o novo {field_name}:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin_edit_product_{product_id}")]
                ])
            )
        
        return PRODUCT_EDIT_STATE
    
    elif data.startswith("admin_toggle_product_"):
        product_id = int(data.replace("admin_toggle_product_", ""))
        
        product_service = ProductService()
        result = await product_service.toggle_product(product_id, admin_id)
        
        if result['success']:
            await query.answer(f"Produto {result['status']} com sucesso!", show_alert=True)
        else:
            await query.answer("Erro ao alterar status.", show_alert=True)
        
        return await admin_product_edit(update, context)
    
    return PRODUCTS_LIST_STATE


async def admin_product_save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva edição de campo do produto"""
    admin_id = update.effective_user.id
    
    if not settings.is_admin(admin_id):
        return ConversationHandler.END
    
    product_id = context.user_data.get('admin_edit_product_id')
    field = context.user_data.get('admin_edit_field')
    
    if not product_id or not field:
        return ConversationHandler.END
    
    # Processa imagem
    if field == 'image' and update.message.photo:
        file_id = update.message.photo[-1].file_id
        
        product_service = ProductService()
        result = await product_service.update_product_image(product_id, file_id, admin_id)
        
        if result['success']:
            await update.message.reply_text(
                "✅ Imagem atualizada com sucesso!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Voltar", callback_data=f"admin_edit_product_{product_id}")]
                ])
            )
    else:
        # Processa texto
        value = update.message.text
        
        if field == 'price':
            try:
                value = float(value.replace(",", "."))
            except ValueError:
                await update.message.reply_text("❌ Preço inválido.")
                return PRODUCT_EDIT_STATE
        
        product_service = ProductService()
        result = await product_service.update_product_field(product_id, field, value, admin_id)
        
        if result['success']:
            await update.message.reply_text(
                f"✅ Campo '{field}' atualizado com sucesso!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋
