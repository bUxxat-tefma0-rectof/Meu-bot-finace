"""
LOJA DE GIFTCARDS - Sistema Principal
Bot Telegram + Painel Admin + Pagamentos PIX
Versão: 1.0.0

Para deploy no Render:
- Configure as variáveis de ambiente no painel do Render
- Use o comando: python main.py
- Tipo: Background Worker
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import nest_asyncio
nest_asyncio.apply()

sys.path.insert(0, str(Path(__file__).parent))

STORAGE_DIRS = [
    "storage", "storage/media", "storage/media/products",
    "storage/media/categories", "storage/media/banners",
    "storage/media/temp", "storage/media/exports",
    "storage/media/backups", "logs",
]

for dir_path in STORAGE_DIRS:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    gitkeep = Path(dir_path) / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler, PicklePersistence,
)
from config import settings
from database.connection import init_db, create_tables, close_db, check_connection

from bot.handlers.start import start_command, verify_subscription, subscription_callback, BLOCKED_STATE, WELCOME_STATE
from bot.handlers.menu import menu_command, menu_callback, button_callback, MENU_MAIN
from bot.handlers.catalog import catalog_command, category_selection, CATALOG_STATE
from bot.handlers.products import product_view, buy_product, confirm_purchase, PRODUCT_STATE
from bot.handlers.profile import profile_command, profile_callback, PROFILE_STATE
from bot.handlers.wallet import wallet_menu, add_balance, process_pix_value, WALLET_STATE, PIX_VALUE_STATE
from bot.handlers.pix import pix_command, pix_value_input, pix_cancel, pix_check, generate_pix, PIX_STATE
from bot.handlers.history import history_command, history_detail, HISTORY_STATE
from bot.handlers.affiliates import affiliates_command, affiliates_info, AFFILIATE_STATE
from bot.handlers.support import support_command, support_message, SUPPORT_STATE

from services.users import UserService
from services.products import ProductService
from services.inventory import InventoryService
from services.orders import OrderService
from services.wallet import WalletService
from services.affiliates import AffiliateService
from services.messages import MessageService
from services.media import MediaService
from services.notifications import NotificationService
from services.cleanup import CleanupService

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/bot.log", encoding="utf-8")],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

user_service = UserService()
product_service = ProductService()
inventory_service = InventoryService()
order_service = OrderService()
wallet_service = WalletService()
affiliate_service = AffiliateService()
message_service = MessageService()
media_service = MediaService()
notification_service = NotificationService()
cleanup_service = CleanupService()


class GiftCardBot:
    def __init__(self):
        self.application = None
        self.services = {
            'users': user_service, 'products': product_service,
            'inventory': inventory_service, 'orders': order_service,
            'wallet': wallet_service, 'affiliates': affiliate_service,
            'messages': message_service, 'media': media_service,
            'notifications': notification_service, 'cleanup': cleanup_service,
        }

    async def initialize(self):
        try:
            logger.info("=" * 50)
            logger.info("🚀 LOJA DE GIFTCARDS - Iniciando...")
            logger.info("=" * 50)
            if not settings.BOT_TOKEN:
                logger.error("❌ BOT_TOKEN não configurado!")
                sys.exit(1)
            logger.info("📊 Conectando ao banco de dados...")
            await init_db()
            if not await check_connection():
                logger.error("❌ Falha na conexão com banco de dados")
                sys.exit(1)
            await create_tables()
            logger.info("✅ Banco de dados inicializado!")
            persistence = PicklePersistence(filepath="bot_persistence.pickle")
            logger.info("🤖 Configurando bot do Telegram...")
            self.application = ApplicationBuilder().token(settings.BOT_TOKEN).persistence(persistence).concurrent_updates(True).build()
            self.application.bot_data['services'] = self.services
            self.application.bot_data['settings'] = settings
            self._register_handlers()
            self._start_background_tasks()
            logger.info("✅ Bot configurado com sucesso!")
            logger.info(f"📢 Canal: {settings.REQUIRED_CHANNEL_LINK}")
            logger.info(f"💳 PIX: {settings.PIX_PROVIDER} ({settings.PIX_ENVIRONMENT})")
            logger.info(f"💰 Min: R$ {settings.PIX_MIN_VALUE:.2f} | Max: R$ {settings.PIX_MAX_VALUE:.2f}")
            logger.info("=" * 50)
        except Exception as e:
            logger.error(f"❌ Erro durante inicialização: {e}", exc_info=True)
            raise

    def _register_handlers(self):
        # ===========================================
        # HANDLERS DO BOT
        # ===========================================
        
        # /start
        start_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_command)],
            states={
                BLOCKED_STATE: [
                    CallbackQueryHandler(verify_subscription, pattern='^verify_subscription$'),
                    CallbackQueryHandler(subscription_callback, pattern='^subscribe_channel$'),
                ],
            },
            fallbacks=[CommandHandler('start', start_command)],
            name="start_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(start_conv_handler)

        # Menu Principal
        menu_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('menu', menu_command),
                CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                CallbackQueryHandler(menu_callback, pattern='^back_to_menu$'),
            ],
            states={
                MENU_MAIN: [CallbackQueryHandler(button_callback, pattern='^btn_')],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="menu_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(menu_conv_handler)

        # Catálogo
        catalog_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(catalog_command, pattern='^btn_buy_giftcard$'),
                CallbackQueryHandler(catalog_command, pattern='^back_to_catalog$'),
            ],
            states={
                CATALOG_STATE: [
                    CallbackQueryHandler(category_selection, pattern='^category_'),
                    CallbackQueryHandler(catalog_command, pattern='^back_to_catalog$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="catalog_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(catalog_conv_handler)

        # Produtos
        product_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(product_view, pattern='^product_')],
            states={
                PRODUCT_STATE: [
                    CallbackQueryHandler(confirm_purchase, pattern='^confirm_purchase_'),
                    CallbackQueryHandler(category_selection, pattern='^back_to_category$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                    CallbackQueryHandler(menu_callback, pattern='^go_to_wallet$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="product_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(product_conv_handler)

        # Perfil
        profile_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(profile_command, pattern='^btn_my_profile$')],
            states={
                PROFILE_STATE: [
                    CallbackQueryHandler(profile_callback, pattern='^go_to_wallet$'),
                    CallbackQueryHandler(profile_callback, pattern='^btn_history$'),
                    CallbackQueryHandler(profile_callback, pattern='^btn_affiliates$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="profile_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(profile_conv_handler)

        # Carteira/Wallet
        wallet_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(wallet_menu, pattern='^btn_add_balance$'),
                CallbackQueryHandler(wallet_menu, pattern='^go_to_wallet$'),
            ],
            states={
                WALLET_STATE: [
                    CallbackQueryHandler(add_balance, pattern='^add_balance_pix$'),
                    CallbackQueryHandler(add_balance, pattern='^quick_values$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
                PIX_VALUE_STATE: [
                    CallbackQueryHandler(process_pix_value, pattern='^pix_value_'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_pix_value),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="wallet_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(wallet_conv_handler)

        # PIX
        pix_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('pix', pix_command),
                CallbackQueryHandler(pix_check, pattern='^check_pix_'),
                CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_'),
            ],
            states={
                PIX_STATE: [
                    CallbackQueryHandler(pix_check, pattern='^check_pix_'),
                    CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="pix_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(pix_conv_handler)

        # Histórico
        history_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(history_command, pattern='^btn_history$')],
            states={
                HISTORY_STATE: [
                    CallbackQueryHandler(history_detail, pattern='^history_page_'),
                    CallbackQueryHandler(history_detail, pattern='^history_detail_'),
                    CallbackQueryHandler(history_detail, pattern='^history_back$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="history_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(history_conv_handler)

        # Afiliados
        affiliate_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(affiliates_command, pattern='^btn_affiliates$')],
            states={
                AFFILIATE_STATE: [
                    CallbackQueryHandler(affiliates_info, pattern='^copy_affiliate_link$'),
                    CallbackQueryHandler(affiliates_info, pattern='^affiliate_referrals$'),
                    CallbackQueryHandler(affiliates_info, pattern='^affiliate_commissions$'),
                    CallbackQueryHandler(affiliates_info, pattern='^share_affiliate_link$'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="affiliate_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(affiliate_conv_handler)

        # Suporte
        support_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(support_command, pattern='^btn_support$')],
            states={
                SUPPORT_STATE: [
                    CallbackQueryHandler(support_message, pattern='^support_faq$'),
                    CallbackQueryHandler(support_message, pattern='^support_report$'),
                    CallbackQueryHandler(support_message, pattern='^support_suggestion$'),
                    CallbackQueryHandler(support_command, pattern='^btn_support$'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, support_message),
                    CallbackQueryHandler(menu_callback, pattern='^menu_main$'),
                ],
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="support_conversation", persistent=True, allow_reentry=True,
        )
        self.application.add_handler(support_conv_handler)
        # ===========================================
        # HANDLERS ADMIN
        # ===========================================
        from admin.handlers.dashboard import admin_dashboard, refresh_dashboard, DASHBOARD_STATE
        from admin.handlers.users import admin_users_list, admin_user_detail, admin_user_info, admin_add_balance, admin_remove_balance, admin_process_balance, admin_block_user, USERS_LIST_STATE, USER_DETAIL_STATE, USER_EDIT_STATE
        from admin.handlers.products import admin_products_list, admin_product_create, admin_product_create_step, admin_product_edit, admin_product_edit_field, admin_product_save_edit, admin_product_delete, admin_product_confirm_delete, PRODUCTS_LIST_STATE, PRODUCT_EDIT_STATE, PRODUCT_CREATE_STATE
        from admin.handlers.stock import admin_stock_manage, admin_stock_add_select, admin_stock_add_items, admin_stock_process_items, admin_stock_available, admin_stock_view_items, admin_stock_export, STOCK_LIST_STATE, STOCK_ADD_STATE
        from admin.handlers.payments import admin_payments_list, admin_payment_filter, admin_payment_detail, admin_payment_show_detail, PAYMENTS_LIST_STATE, PAYMENT_DETAIL_STATE
        from admin.handlers.settings import admin_settings, admin_settings_pix, admin_settings_messages, admin_settings_edit_message, admin_settings_save_message, admin_test_pix_connection, SETTINGS_MAIN_STATE, SETTINGS_EDIT_STATE
        from admin.handlers.notifications import admin_notifications, admin_toggle_notification, NOTIFICATIONS_STATE

        # Admin Dashboard
        self.application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('admin', admin_dashboard), CallbackQueryHandler(admin_dashboard, pattern='^admin_dashboard$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$'), CallbackQueryHandler(refresh_dashboard, pattern='^admin_refresh_dashboard$')],
            states={DASHBOARD_STATE: [CallbackQueryHandler(admin_users_list, pattern='^admin_users$'), CallbackQueryHandler(admin_products_list, pattern='^admin_products$'), CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock$'), CallbackQueryHandler(admin_payments_list, pattern='^admin_payments$'), CallbackQueryHandler(admin_settings, pattern='^admin_settings$'), CallbackQueryHandler(admin_notifications, pattern='^admin_notifications$'), CallbackQueryHandler(refresh_dashboard, pattern='^admin_refresh_dashboard$')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_dashboard", persistent=True,
        ))

        # Admin Usuários
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_users_list, pattern='^admin_users$'), CallbackQueryHandler(admin_users_list, pattern='^admin_users_list$')],
            states={USERS_LIST_STATE: [CallbackQueryHandler(admin_user_detail, pattern='^admin_users_page_'), CallbackQueryHandler(admin_user_detail, pattern='^admin_users_search$'), CallbackQueryHandler(admin_user_detail, pattern='^admin_users_detail$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], USER_DETAIL_STATE: [CallbackQueryHandler(admin_add_balance, pattern='^admin_add_balance_'), CallbackQueryHandler(admin_remove_balance, pattern='^admin_remove_balance_'), CallbackQueryHandler(admin_block_user, pattern='^admin_block_user_'), CallbackQueryHandler(admin_block_user, pattern='^admin_unblock_user_'), CallbackQueryHandler(admin_users_list, pattern='^admin_users_list$'), MessageHandler(filters.TEXT & ~filters.COMMAND, admin_user_info)], USER_EDIT_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_balance), CallbackQueryHandler(admin_user_detail, pattern='^admin_user_detail_')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_users", persistent=True,
        ))

        # Admin Produtos
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_products_list, pattern='^admin_products$'), CallbackQueryHandler(admin_products_list, pattern='^admin_products_list$')],
            states={PRODUCTS_LIST_STATE: [CallbackQueryHandler(admin_product_create, pattern='^admin_product_create$'), CallbackQueryHandler(admin_product_edit, pattern='^admin_product_edit_select$'), CallbackQueryHandler(admin_product_delete, pattern='^admin_product_delete$'), CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock_manage$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], PRODUCT_EDIT_STATE: [CallbackQueryHandler(admin_product_edit_field, pattern='^admin_edit_field_'), CallbackQueryHandler(admin_product_edit_field, pattern='^admin_toggle_product_'), CallbackQueryHandler(admin_product_confirm_delete, pattern='^admin_confirm_delete_'), CallbackQueryHandler(admin_products_list, pattern='^admin_products_list$'), MessageHandler(filters.TEXT & ~filters.COMMAND, admin_product_save_edit), MessageHandler(filters.PHOTO, admin_product_save_edit)], PRODUCT_CREATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_product_create_step), CallbackQueryHandler(admin_products_list, pattern='^admin_products_list$')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_products", persistent=True,
        ))

        # Admin Estoque
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock_manage$'), CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock$')],
            states={STOCK_LIST_STATE: [CallbackQueryHandler(admin_stock_add_select, pattern='^admin_stock_add_select$'), CallbackQueryHandler(admin_stock_available, pattern='^admin_stock_available$'), CallbackQueryHandler(admin_stock_view_items, pattern='^admin_view_stock_'), CallbackQueryHandler(admin_stock_export, pattern='^admin_stock_export$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], STOCK_ADD_STATE: [CallbackQueryHandler(admin_stock_add_items, pattern='^admin_stock_add_'), MessageHandler(filters.TEXT & ~filters.COMMAND, admin_stock_process_items), CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock_manage$')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_stock", persistent=True,
        ))

        # Admin Pagamentos
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_payments_list, pattern='^admin_payments$'), CallbackQueryHandler(admin_payments_list, pattern='^admin_payments_list$')],
            states={PAYMENTS_LIST_STATE: [CallbackQueryHandler(admin_payment_filter, pattern='^admin_filter_'), CallbackQueryHandler(admin_payment_detail, pattern='^admin_payment_detail$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], PAYMENT_DETAIL_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_payment_show_detail), CallbackQueryHandler(admin_payments_list, pattern='^admin_payments_list$')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_payments", persistent=True,
        ))

        # Admin Configurações
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_settings, pattern='^admin_settings$')],
            states={SETTINGS_MAIN_STATE: [CallbackQueryHandler(admin_settings_pix, pattern='^admin_settings_pix$'), CallbackQueryHandler(admin_settings_messages, pattern='^admin_settings_messages$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], SETTINGS_EDIT_STATE: [CallbackQueryHandler(admin_settings_edit_message, pattern='^admin_edit_message_'), CallbackQueryHandler(admin_test_pix_connection, pattern='^admin_test_pix_connection$'), CallbackQueryHandler(admin_settings, pattern='^admin_settings$'), CallbackQueryHandler(admin_settings_messages, pattern='^admin_settings_messages$'), MessageHandler(filters.TEXT & ~filters.COMMAND, admin_settings_save_message)]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_settings", persistent=True,
        ))

        # Admin Notificações
        self.application.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_notifications, pattern='^admin_notifications$')],
            states={NOTIFICATIONS_STATE: [CallbackQueryHandler(admin_toggle_notification, pattern='^admin_notify_'), CallbackQueryHandler(admin_toggle_notification, pattern='^admin_toggle_notify_'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')]},
            fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin_notifications", persistent=True,
        ))

        # Handler de mensagens não reconhecidas
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_unknown_text))
        self.application.add_error_handler(self._handle_error)
        logger.info("✅ Todos os handlers registrados!")

    def _start_background_tasks(self):
        job_queue = self.application.job_queue
        job_queue.run_repeating(cleanup_service.clean_temp_messages, interval=300, first=10, name="cleanup_temp_messages")
        job_queue.run_repeating(wallet_service.check_expired_pix, interval=60, first=30, name="check_expired_pix")
        job_queue.run_repeating(product_service.update_statistics, interval=600, first=60, name="update_statistics")
        job_queue.run_repeating(notification_service.check_pending_notifications, interval=300, first=20, name="check_notifications")
        logger.info("✅ Tarefas em background iniciadas!")

    async def _handle_unknown_text(self, update, context):
        user_id = update.effective_user.id
        text = update.message.text[:50] if update.message.text else ""
        logger.info(f"Mensagem não reconhecida de {user_id}: {text}")
        await update.message.reply_text("❓ Comando não reconhecido.\n\nUse /menu para ver as opções disponíveis\nUse /start para reiniciar o bot\nUse /pix para fazer uma recarga\nUse /admin para painel administrativo")

    async def _handle_error(self, update, context):
        logger.error(f"Erro no bot: {context.error}", exc_info=context.error)
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text("❌ Ocorreu um erro inesperado.\nPor favor, tente novamente ou use /start para reiniciar.")
        except Exception:
            pass

    async def start(self):
        try:
            await self.initialize()
            logger.info("🤖 Bot iniciado em modo polling...")
            logger.info("📊 Pressione Ctrl+C para parar")
            logger.info("=" * 50)
            await self.application.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)
        except KeyboardInterrupt:
            logger.info("👋 Bot parado manualmente")
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        try:
            logger.info("🧹 Executando limpeza...")
            await close_db()
            if self.application and hasattr(self.application, 'persistence'):
                await self.application.persistence.flush()
            logger.info("✅ Limpeza concluída. Bot encerrado.")
        except Exception as e:
            logger.error(f"❌ Erro durante limpeza: {e}")


# ===========================================
# PONTO DE ENTRADA PRINCIPAL
# ===========================================

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if not settings.BOT_TOKEN:
        logger.error("=" * 50)
        logger.error("❌ ERRO: BOT_TOKEN não configurado!")
        logger.error("=" * 50)
        sys.exit(1)
    bot = GiftCardBot()
    asyncio.run(bot.start())
