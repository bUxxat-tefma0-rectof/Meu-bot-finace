"""
Camada de Serviços
Orquestra a lógica de negócio entre handlers e repositórios
"""

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

__all__ = [
    "UserService",
    "ProductService",
    "InventoryService",
    "OrderService",
    "WalletService",
    "AffiliateService",
    "MessageService",
    "MediaService",
    "NotificationService",
    "CleanupService",
]
