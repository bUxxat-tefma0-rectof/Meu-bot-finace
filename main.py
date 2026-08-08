"""
LOJA DE GIFTCARDS - Sistema Principal
Bot Telegram + Painel Admin + Pagamentos PIX
Versão: 1.0.0
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

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, PicklePersistence
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

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/bot.log", encoding="utf-8")])
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
        self.services = {'users': user_service, 'products': product_service, 'inventory': inventory_service, 'orders': order_service, 'wallet': wallet_service, 'affiliates': affiliate_service, 'messages': message_service, 'media': media_service, 'notifications': notification_service, 'cleanup': cleanup_service}

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
        self.application.add_handler(ConversationHandler(entry_points=[CommandHandler('start', start_command)], states={BLOCKED_STATE: [CallbackQueryHandler(verify_subscription, pattern='^verify_subscription$'), CallbackQueryHandler(subscription_callback, pattern='^subscribe_channel$')]}, fallbacks=[CommandHandler('start', start_command)], name="start", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CommandHandler('menu', menu_command), CallbackQueryHandler(menu_callback, pattern='^menu_main$'), CallbackQueryHandler(menu_callback, pattern='^back_to_menu$')], states={MENU_MAIN: [CallbackQueryHandler(button_callback, pattern='^btn_')]}, fallbacks=[CommandHandler('menu', menu_command)], name="menu", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(catalog_command, pattern='^btn_buy_giftcard$'), CallbackQueryHandler(catalog_command, pattern='^back_to_catalog$')], states={CATALOG_STATE: [CallbackQueryHandler(category_selection, pattern='^category_'), CallbackQueryHandler(catalog_command, pattern='^back_to_catalog$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="catalog", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(product_view, pattern='^product_')], states={PRODUCT_STATE: [CallbackQueryHandler(confirm_purchase, pattern='^confirm_purchase_'), CallbackQueryHandler(category_selection, pattern='^back_to_category$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$'), CallbackQueryHandler(menu_callback, pattern='^go_to_wallet$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="product", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(profile_command, pattern='^btn_my_profile$')], states={PROFILE_STATE: [CallbackQueryHandler(profile_callback, pattern='^go_to_wallet$'), CallbackQueryHandler(profile_callback, pattern='^btn_history$'), CallbackQueryHandler(profile_callback, pattern='^btn_affiliates$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="profile", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(wallet_menu, pattern='^btn_add_balance$'), CallbackQueryHandler(wallet_menu, pattern='^go_to_wallet$')], states={WALLET_STATE: [CallbackQueryHandler(add_balance, pattern='^add_balance_pix$'), CallbackQueryHandler(add_balance, pattern='^quick_values$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')], PIX_VALUE_STATE: [CallbackQueryHandler(process_pix_value, pattern='^pix_value_'), MessageHandler(filters.TEXT & ~filters.COMMAND, process_pix_value), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="wallet", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CommandHandler('pix', pix_command), CallbackQueryHandler(pix_check, pattern='^check_pix_'), CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_')], states={PIX_STATE: [CallbackQueryHandler(pix_check, pattern='^check_pix_'), CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="pix", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(history_command, pattern='^btn_history$')], states={HISTORY_STATE: [CallbackQueryHandler(history_detail, pattern='^history_page_'), CallbackQueryHandler(history_detail, pattern='^history_detail_'), CallbackQueryHandler(history_detail, pattern='^history_back$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="history", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(affiliates_command, pattern='^btn_affiliates$')], states={AFFILIATE_STATE: [CallbackQueryHandler(affiliates_info, pattern='^affiliate_referrals$'), CallbackQueryHandler(affiliates_info, pattern='^affiliate_commissions$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="affiliate", persistent=True, allow_reentry=True))
        self.application.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(support_command, pattern='^btn_support$')], states={SUPPORT_STATE: [CallbackQueryHandler(support_message, pattern='^support_faq$'), CallbackQueryHandler(support_command, pattern='^btn_support$'), CallbackQueryHandler(menu_callback, pattern='^menu_main$')]}, fallbacks=[CommandHandler('menu', menu_command)], name="support", persistent=True, allow_reentry=True))

        from admin.handlers.dashboard import admin_dashboard, refresh_dashboard, DASHBOARD_STATE
        from admin.handlers.users import admin_users_list, USERS_LIST_STATE
        from admin.handlers.products import admin_products_list, PRODUCTS_LIST_STATE
        from admin.handlers.stock import admin_stock_manage, STOCK_LIST_STATE
        from admin.handlers.payments import admin_payments_list, PAYMENTS_LIST_STATE
        from admin.handlers.settings import admin_settings, SETTINGS_MAIN_STATE
        from admin.handlers.notifications import admin_notifications, NOTIFICATIONS_STATE

        self.application.add_handler(ConversationHandler(entry_points=[CommandHandler('admin', admin_dashboard), CallbackQueryHandler(admin_dashboard, pattern='^admin_dashboard$'), CallbackQueryHandler(admin_dashboard, pattern='^admin_back_to_dashboard$')], states={DASHBOARD_STATE: [CallbackQueryHandler(admin_users_list, pattern='^admin_users$'), CallbackQueryHandler(admin_products_list, pattern='^admin_products$'), CallbackQueryHandler(admin_stock_manage, pattern='^admin_stock$'), CallbackQueryHandler(admin_payments_list, pattern='^admin_payments$'), CallbackQueryHandler(admin_settings, pattern='^admin_settings$'), CallbackQueryHandler(admin_notifications, pattern='^admin_notifications$')]}, fallbacks=[CommandHandler('admin', admin_dashboard)], name="admin", persistent=True))

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_unknown_text))
        self.application.add_error_handler(self._handle_error)
        logger.info("✅ Todos os handlers registrados!")

    def _start_background_tasks(self):
        job_queue = self.application.job_queue
        job_queue.run_repeating(cleanup_service.clean_temp_messages, interval=300, first=10, name="cleanup")
        job_queue.run_repeating(wallet_service.check_expired_pix, interval=60, first=30, name="pix_check")
        job_queue.run_repeating(product_service.update_statistics, interval=600, first=60, name="stats")
        job_queue.run_repeating(notification_service.check_pending_notifications, interval=300, first=20, name="notif")
        logger.info("✅ Tarefas em background iniciadas!")

    async def _handle_unknown_text(self, update, context):
        await update.message.reply_text("❓ Comando não reconhecido.\n\nUse /menu para ver as opções disponíveis\nUse /start para reiniciar o bot\nUse /pix para fazer uma recarga\nUse /admin para painel administrativo")

    async def _handle_error(self, update, context):
        logger.error(f"Erro no bot: {context.error}", exc_info=context.error)
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text("❌ Ocorreu um erro. Use /start para reiniciar.")
        except Exception: pass

    async def start(self):
        try:
            await self.initialize()
            logger.info("🤖 Bot iniciado em modo polling...")
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
            logger.info("✅ Limpeza concluída.")
        except Exception as e:
            logger.error(f"❌ Erro durante limpeza: {e}")

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
