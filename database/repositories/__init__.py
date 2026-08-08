"""
Repositórios de acesso a dados
Cada repositório encapsula operações de uma entidade
"""

from database.repositories.user_repository import UserRepository
from database.repositories.product_repository import ProductRepository
from database.repositories.order_repository import OrderRepository
from database.repositories.payment_repository import PaymentRepository
from database.repositories.affiliate_repository import AffiliateRepository
from database.repositories.inventory_repository import InventoryRepository
from database.repositories.message_repository import MessageRepository
from database.repositories.setting_repository import SettingRepository
from database.repositories.audit_repository import AuditRepository

__all__ = [
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "PaymentRepository",
    "AffiliateRepository",
    "InventoryRepository",
    "MessageRepository",
    "SettingRepository",
    "AuditRepository",
]
