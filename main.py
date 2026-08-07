"""
LOJA DE GIFTCARDS - Sistema Principal
Bot Telegram + Painel Admin + Pagamentos PIX
Versão: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    PicklePersistence
)

from config import settings
from database.connection import init_db, create_tables, close_db

# Import dos handlers do bot
from bot.handlers.start import (
    start_command,
    verify_subscription,
    subscription_callback,
    BLOCKED_STATE
)

from bot.handlers.menu import (
    menu_command,
    menu_callback,
    button_callback,
    MENU_MAIN
)

from bot.handlers.catalog import (
    catalog_command,
    category_selection,
    CATALOG_STATE
)

from bot.handlers.products import (
    product_view,
    buy_product,
    confirm_purchase,
    PRODUCT_STATE
)

from bot.handlers.profile import (
    profile_command,
    profile_callback,
    PROFILE_STATE
)

from bot.handlers.wallet import (
    wallet_menu,
    add_balance,
    WALLET_STATE
)

from bot.handlers.pix import (
    pix_command,
    pix_value_input,
    pix_cancel,
    pix_check,
    PIX_STATE
)

from bot.handlers.history import (
    history_command,
    history_detail,
    HISTORY_STATE
)

from bot.handlers.affiliates import (
    affiliates_command,
    affiliates_info,
    AFFILIATE_STATE
)

from bot.handlers.support import (
    support_command,
    support_message,
    SUPPORT_STATE
)

# Import dos serviços
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

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Instâncias dos serviços
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
    """Classe principal do Bot de Gift Cards"""
    
    def __init__(self):
        self.application = None
        self.services = {
            'users': user_service,
            'products': product_service,
            'inventory': inventory_service,
            'orders': order_service,
            'wallet': wallet_service,
            'affiliates': affiliate_service,
            'messages': message_service,
            'media': media_service,
            'notifications': notification_service,
            'cleanup': cleanup_service
        }
    
    async def initialize(self):
        """Inicializa todos os componentes do bot"""
        try:
            logger.info("🚀 Iniciando LOJA DE GIFTCARDS...")
            
            # Inicializa banco de dados
            logger.info("📊 Conectando ao banco de dados...")
            await init_db()
            await create_tables()
            logger.info("✅ Banco de dados inicializado com sucesso!")
            
            # Configura persistência para manter dados entre reinicializações
            persistence = PicklePersistence(filepath="bot_persistence.pickle")
            
            # Cria a aplicação do bot
            logger.info("🤖 Configurando bot do Telegram...")
            self.application = (
                ApplicationBuilder()
                .token(settings.BOT_TOKEN)
                .persistence(persistence)
                .concurrent_updates(True)
                .build()
            )
            
            # Compartilha serviços com os handlers
            self.application.bot_data['services'] = self.services
            self.application.bot_data['settings'] = settings
            
            # Registra todos os handlers
            self._register_handlers()
            
            # Inicia tarefas em background
            self._start_background_tasks()
            
            logger.info("✅ Bot configurado e pronto para iniciar!")
            logger.info(f"📢 Canal obrigatório: {settings.REQUIRED_CHANNEL_LINK}")
            
        except Exception as e:
            logger.error(f"❌ Erro durante inicialização: {e}")
            raise
    
    def _register_handlers(self):
        """Registra todos os handlers do bot"""
        
        # Handler principal - Comando /start com verificação de canal
        start_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_command)],
            states={
                BLOCKED_STATE: [
                    CallbackQueryHandler(verify_subscription, pattern='^verify_subscription$'),
                    CallbackQueryHandler(subscription_callback, pattern='^subscribe_channel$')
                ]
            },
            fallbacks=[CommandHandler('start', start_command)],
            name="start_conversation",
            persistent=True
        )
        self.application.add_handler(start_conv_handler)
        
        # Handler do menu principal
        menu_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('menu', menu_command),
                CallbackQueryHandler(menu_callback, pattern='^menu_')
            ],
            states={
                MENU_MAIN: [
                    CallbackQueryHandler(button_callback, pattern='^btn_'),
                    CallbackQueryHandler(menu_callback, pattern='^menu_')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="menu_conversation",
            persistent=True
        )
        self.application.add_handler(menu_conv_handler)
        
        # Handler do catálogo
        catalog_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(catalog_command, pattern='^catalog_'),
                CallbackQueryHandler(category_selection, pattern='^category_')
            ],
            states={
                CATALOG_STATE: [
                    CallbackQueryHandler(category_selection, pattern='^category_'),
                    CallbackQueryHandler(product_view, pattern='^product_')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="catalog_conversation",
            persistent=True
        )
        self.application.add_handler(catalog_conv_handler)
        
        # Handler de produtos
        product_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(product_view, pattern='^product_'),
                CallbackQueryHandler(buy_product, pattern='^buy_product_')
            ],
            states={
                PRODUCT_STATE: [
                    CallbackQueryHandler(buy_product, pattern='^buy_product_'),
                    CallbackQueryHandler(confirm_purchase, pattern='^confirm_purchase_'),
                    CallbackQueryHandler(menu_callback, pattern='^back_to_menu')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="product_conversation",
            persistent=True
        )
        self.application.add_handler(product_conv_handler)
        
        # Handler de perfil
        profile_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('profile', profile_command),
                CallbackQueryHandler(profile_callback, pattern='^profile_')
            ],
            states={
                PROFILE_STATE: [
                    CallbackQueryHandler(profile_callback, pattern='^profile_'),
                    CallbackQueryHandler(menu_callback, pattern='^back_to_menu')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="profile_conversation",
            persistent=True
        )
        self.application.add_handler(profile_conv_handler)
        
        # Handler de carteira/saldo
        wallet_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('wallet', wallet_menu),
                CallbackQueryHandler(add_balance, pattern='^add_balance')
            ],
            states={
                WALLET_STATE: [
                    CallbackQueryHandler(add_balance, pattern='^add_balance'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, pix_value_input)
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="wallet_conversation",
            persistent=True
        )
        self.application.add_handler(wallet_conv_handler)
        
        # Handler do PIX
        pix_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('pix', pix_command),
                CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_'),
                CallbackQueryHandler(pix_check, pattern='^check_pix_')
            ],
            states={
                PIX_STATE: [
                    CallbackQueryHandler(pix_cancel, pattern='^cancel_pix_'),
                    CallbackQueryHandler(pix_check, pattern='^check_pix_')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="pix_conversation",
            persistent=True
        )
        self.application.add_handler(pix_conv_handler)
        
        # Handler de histórico
        history_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('history', history_command),
                CallbackQueryHandler(history_detail, pattern='^history_')
            ],
            states={
                HISTORY_STATE: [
                    CallbackQueryHandler(history_detail, pattern='^history_'),
                    CallbackQueryHandler(menu_callback, pattern='^back_to_menu')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="history_conversation",
            persistent=True
        )
        self.application.add_handler(history_conv_handler)
        
        # Handler de afiliados
        affiliate_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('affiliates', affiliates_command),
                CallbackQueryHandler(affiliates_info, pattern='^affiliate_')
            ],
            states={
                AFFILIATE_STATE: [
                    CallbackQueryHandler(affiliates_info, pattern='^affiliate_'),
                    CallbackQueryHandler(menu_callback, pattern='^back_to_menu')
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="affiliate_conversation",
            persistent=True
        )
        self.application.add_handler(affiliate_conv_handler)
        
        # Handler de suporte
        support_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('support', support_command),
                CallbackQueryHandler(support_message, pattern='^support_')
            ],
            states={
                SUPPORT_STATE: [
                    CallbackQueryHandler(support_message, pattern='^support_'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)
                ]
            },
            fallbacks=[CommandHandler('menu', menu_command)],
            name="support_conversation",
            persistent=True
        )
        self.application.add_handler(support_conv_handler)
        
        # Handler para mensagens de texto não reconhecidas
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_unknown_text)
        )
        
        # Handler para erros
        self.application.add_error_handler(self._handle_error)
        
        logger.info("✅ Todos os handlers registrados com sucesso!")
    
    def _start_background_tasks(self):
        """Inicia tarefas em background"""
        job_queue = self.application.job_queue
        
        # Limpeza de mensagens temporárias a cada 5 minutos
        job_queue.run_repeating(
            cleanup_service.clean_temp_messages,
            interval=300,
            first=10,
            name="cleanup_temp_messages"
        )
        
        # Verificação de PIX expirados a cada 1 minuto
        job_queue.run_repeating(
            wallet_service.check_expired_pix,
            interval=60,
            first=30,
            name="check_expired_pix"
        )
        
        # Atualização de estatísticas a cada 10 minutos
        job_queue.run_repeating(
            product_service.update_statistics,
            interval=600,
            first=60,
            name="update_statistics"
        )
        
        # Verificação de notificações do canal
        job_queue.run_repeating(
            notification_service.check_pending_notifications,
            interval=300,
            first=20,
            name="check_notifications"
        )
        
        logger.info("✅ Tarefas em background iniciadas!")
    
    async def _handle_unknown_text(self, update, context):
        """Manipula mensagens de texto não reconhecidas"""
        user_id = update.effective_user.id
        logger.info(f"Mensagem não reconhecida do usuário {user_id}: {update.message.text}")
        
        await update.message.reply_text(
            "❓ Comando não reconhecido.\n"
            "Use /menu para ver as opções disponíveis.",
            reply_markup=None
        )
    
    async def _handle_error(self, update, context):
        """Manipula erros do bot"""
        logger.error(f"Erro no bot: {context.error}", exc_info=context.error)
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ocorreu um erro inesperado.\n"
                "Por favor, tente novamente ou use /menu para reiniciar."
            )
    
    async def start(self):
        """Inicia o bot"""
        try:
            await self.initialize()
            
            logger.info("🤖 Bot iniciado em modo polling...")
            logger.info("📊 Pressione Ctrl+C para parar")
            
            # Inicia o bot
            await self.application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            
        except KeyboardInterrupt:
            logger.info("👋 Bot parado manualmente")
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Limpeza final"""
        try:
            logger.info("🧹 Executando limpeza...")
            
            # Fecha conexões com banco de dados
            await close_db()
            
            # Salva dados de persistência
            if self.application and hasattr(self.application, 'persistence'):
                await self.application.persistence.flush()
            
            logger.info("✅ Limpeza concluída. Bot encerrado.")
            
        except Exception as e:
            logger.error(f"❌ Erro durante limpeza: {e}")

# Ponto de entrada principal
if __name__ == '__main__':
    try:
        # Cria e inicia o bot
        bot = GiftCardBot()
        
        # Configura loop de eventos
        if sys.platform == 'win32':
            # Windows precisa de política de loop específica
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Executa o bot
        asyncio.run(bot.start())
        
    except KeyboardInterrupt:
        logger.info("👋 Encerrado pelo usuário")
    except Exception as e:
        logger.critical(f"💥 Erro crítico: {e}", exc_info=True)
        sys.exit(1)
