"""
Handler do Sistema PIX
Geração, verificação e cancelamento de pagamentos PIX
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import settings
from services.wallet import WalletService
from bot.keyboards.menu import get_back_button

logger = logging.getLogger(__name__)

PIX_STATE = 1


async def pix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /pix - Inicia recarga via PIX"""
    user_id = update.effective_user.id
    
    # Verifica se já existe PIX pendente
    wallet_service = WalletService()
    pending_pix = await wallet_service.get_pending_pix(user_id)
    
    if pending_pix:
        # Mostra PIX pendente
        pix_data = pending_pix
        
        message = (
            f"⚠️ Você já tem um PIX pendente!\n\n"
            f"💰 Valor: R$ {pix_data['value']:.2f}\n"
            f"🕒 Expira em: {pix_data['expires_at']}\n\n"
            f"Pague ou aguarde a expiração."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"check_pix_{pix_data['id']}")],
            [InlineKeyboardButton("❌ Cancelar PIX", callback_data=f"cancel_pix_{pix_data['id']}")],
            [get_back_button()]
        ])
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        return PIX_STATE
    
    # Redireciona para carteira
    from bot.handlers.wallet import wallet_menu
    return await wallet_menu(update, context)


async def pix_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa valor digitado para PIX"""
    from bot.handlers.wallet import process_pix_value
    return await process_pix_value(update, context)


async def generate_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera um novo pagamento PIX"""
    user_id = update.effective_user.id
    value = context.user_data.get('pix_value', 0)
    
    if value <= 0:
        return ConversationHandler.END
    
    # Gera PIX via serviço
    wallet_service = WalletService()
    pix_result = await wallet_service.create_pix_payment(user_id, value)
    
    if not pix_result['success']:
        error_msg = pix_result.get('error', 'Erro ao gerar PIX')
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"❌ {error_msg}",
                reply_markup=InlineKeyboardMarkup([[get_back_button()]])
            )
        else:
            await update.message.reply_text(
                f"❌ {error_msg}",
                reply_markup=InlineKeyboardMarkup([[get_back_button()]])
            )
        
        return ConversationHandler.END
    
    # PIX gerado com sucesso
    pix_data = pix_result['pix_data']
    
    pix_message = (
        f"🟢 PAGAMENTO VIA PIX GERADO\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Valor: R$ {value:.2f}\n"
        f"🕒 Validade: {settings.PIX_EXPIRATION_MINUTES} minutos\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📲 Como pagar:\n"
        f"1️⃣ Abra o app do seu banco\n"
        f"2️⃣ Escolha pagar via PIX\n"
        f"3️⃣ Escaneie o QR Code\n\n"
        f"👇 Ou copie o código abaixo:\n\n"
        f"<code>{pix_data['pix_code']}</code>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"check_pix_{pix_data['id']}")],
        [InlineKeyboardButton("📋 Copiar Código", callback_data=f"copy_pix_{pix_data['id']}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_pix_{pix_data['id']}")],
        [get_back_button()]
    ])
    
    # Envia QR Code se disponível
    if update.callback_query:
        await update.callback_query.edit_message_text("⏳ Gerando QR Code PIX...")
        
        if pix_data.get('qr_code_image'):
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=pix_data['qr_code_image'],
                    caption=pix_message,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Erro ao enviar QR Code: {e}")
                await update.callback_query.edit_message_text(
                    pix_message,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        else:
            await update.callback_query.edit_message_text(
                pix_message,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    else:
        await update.message.reply_text(
            pix_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    # Agenda verificação automática
    context.job_queue.run_once(
        auto_check_pix,
        settings.PIX_POLL_INTERVAL,
        chat_id=update.effective_chat.id,
        user_id=user_id,
        data={'pix_id': pix_data['id']}
    )
    
    return PIX_STATE


async def pix_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica status do pagamento PIX"""
    query = update.callback_query
    await query.answer("Verificando pagamento...")
    
    pix_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    
    wallet_service = WalletService()
    result = await wallet_service.check_pix_status(pix_id)
    
    if result['status'] == 'approved':
        # Pagamento confirmado
        approved_message = settings.PIX_APPROVED.format(
            valor=f"{result['value']:.2f}",
            saldo_anterior=f"{result['old_balance']:.2f}",
            saldo_atual=f"{result['new_balance']:.2f}"
        )
        
        await query.edit_message_text(
            approved_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Comprar Gift Cards", callback_data="btn_buy_giftcard")],
                [get_back_button()]
            ]),
            parse_mode=ParseMode.HTML
        )
        
        # Notifica
        from services.notifications import NotificationService
        notification_service = NotificationService()
        await notification_service.notify_pix_approved(user_id, result, context)
        
        return ConversationHandler.END
    
    elif result['status'] == 'expired':
        # PIX expirado
        expired_message = settings.PIX_EXPIRED.format(
            valor=f"{result['value']:.2f}"
        )
        
        await query.edit_message_text(
            expired_message,
            reply_markup=InlineKeyboardMarkup([[get_back_button()]]),
            parse_mode=ParseMode.HTML
        )
        
        return ConversationHandler.END
    
    else:
        # Ainda pendente
        await query.edit_message_text(
            f"⏳ Pagamento ainda não confirmado.\n"
            f"💰 Valor: R$ {result['value']:.2f}\n\n"
            f"Tente novamente em alguns instantes.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"check_pix_{pix_id}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_pix_{pix_id}")],
                [get_back_button()]
            ])
        )
        
        return PIX_STATE


async def pix_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela um PIX pendente"""
    query = update.callback_query
    await query.answer()
    
    pix_id = int(query.data.split("_")[-1])
    
    wallet_service = WalletService()
    result = await wallet_service.cancel_pix(pix_id)
    
    if result['success']:
        await query.edit_message_text(
            "✅ PIX cancelado com sucesso.\n"
            "Nenhum valor foi debitado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💠 Novo PIX", callback_data="add_balance_pix")],
                [get_back_button()]
            ])
        )
    else:
        await query.edit_message_text(
            "❌ Não foi possível cancelar este PIX.",
            reply_markup=InlineKeyboardMarkup([[get_back_button()]])
        )
    
    return ConversationHandler.END


async def auto_check_pix(context: ContextTypes.DEFAULT_TYPE):
    """Verificação automática de PIX (job)"""
    job_data = context.job.data
    pix_id = job_data['pix_id']
    user_id = job_data['user_id']
    
    wallet_service = WalletService()
    result = await wallet_service.check_pix_status(pix_id)
    
    if result['status'] == 'approved':
        # Notifica usuário
        approved_message = settings.PIX_APPROVED.format(
            valor=f"{result['value']:.2f}",
            saldo_anterior=f"{result['old_balance']:.2f}",
            saldo_atual=f"{result['new_balance']:.2f}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=approved_message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Comprar Gift Cards", callback_data="btn_buy_giftcard")]
                ]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Erro ao notificar pagamento aprovado: {e}")
    
    elif result['status'] == 'pending':
        # Reagenda verificação
        context.job_queue.run_once(
            auto_check_pix,
            settings.PIX_POLL_INTERVAL,
            chat_id=user_id,
            user_id=user_id,
            data={'pix_id': pix_id}
        )
