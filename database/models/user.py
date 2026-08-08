"""
Modelo de Usuário
"""

from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Float, Integer, 
    Boolean, DateTime, Text, Index
)
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    """Usuário do bot"""
    
    __tablename__ = "users"
    
    # Identificação
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    
    # Financeiro
    balance = Column(Float, default=0.0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    total_purchases = Column(Integer, default=0, nullable=False)
    
    # Afiliado
    referrer_id = Column(BigInteger, nullable=True, index=True)
    affiliate_earnings = Column(Float, default=0.0, nullable=False)
    total_referrals = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Metadados
    language = Column(String(10), default="pt-br")
    notes = Column(Text, nullable=True)
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    orders = relationship("Order", back_populates="user", lazy="dynamic")
    payments = relationship("Payment", back_populates="user", lazy="dynamic")
    sessions = relationship("UserSession", back_populates="user", lazy="dynamic")
    
    # Índices
    __table_args__ = (
        Index("idx_user_telegram_id", "telegram_id"),
        Index("idx_user_referrer", "referrer_id"),
        Index("idx_user_balance", "balance"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name={self.first_name})>"
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "balance": self.balance,
            "total_spent": self.total_spent,
            "total_purchases": self.total_purchases,
            "referrer_id": self.referrer_id,
            "affiliate_earnings": self.affiliate_earnings,
            "total_referrals": self.total_referrals,
            "is_active": self.is_active,
            "is_blocked": self.is_blocked,
            "is_admin": self.is_admin,
            "language": self.language,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M") if self.updated_at else None,
            "last_activity": self.last_activity.strftime("%d/%m/%Y %H:%M") if self.last_activity else None,
        }
