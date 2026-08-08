"""
Modelo de Administrador e Permissões
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, 
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
import enum

from database.connection import Base


class AdminRole(str, enum.Enum):
    """Papéis dos administradores"""
    OWNER = "owner"          # Dono - acesso total
    MANAGER = "manager"      # Gerente - produtos, estoque, usuários
    FINANCIAL = "financial"  # Financeiro - pagamentos e saldo
    STOCK = "stock"          # Estoquista - somente estoque
    SUPPORT = "support"      # Suporte - atendimento


class Admin(Base):
    """Administrador do sistema"""
    
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(150), nullable=True)
    
    # Papel e permissões
    role = Column(Enum(AdminRole), default=AdminRole.MANAGER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadados
    created_by = Column(BigInteger, nullable=True)  # Telegram ID de quem criou
    notes = Column(Text, nullable=True)
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relacionamentos
    permissions = relationship("AdminPermission", back_populates="admin", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Admin(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "last_login": self.last_login.strftime("%d/%m/%Y %H:%M") if self.last_login else None,
        }


class AdminPermission(Base):
    """Permissões específicas do administrador"""
    
    __tablename__ = "admin_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)
    
    # Permissões
    can_manage_users = Column(Boolean, default=False)
    can_manage_products = Column(Boolean, default=False)
    can_manage_stock = Column(Boolean, default=False)
    can_manage_payments = Column(Boolean, default=False)
    can_manage_affiliates = Column(Boolean, default=False)
    can_manage_settings = Column(Boolean, default=False)
    can_manage_admins = Column(Boolean, default=False)
    can_view_logs = Column(Boolean, default=False)
    can_export_data = Column(Boolean, default=False)
    can_send_notifications = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    admin = relationship("Admin", back_populates="permissions")
    
    def __repr__(self):
        return f"<AdminPermission(admin_id={self.admin_id})>"
