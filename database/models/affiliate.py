"""
Modelo de Afiliados e Comissões
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, Float, String, 
    Boolean, DateTime, Text
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Affiliate(Base):
    """Relação de afiliado"""
    
    __tablename__ = "affiliates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Afiliador (quem indicou)
    referrer_id = Column(BigInteger, nullable=False, index=True)
    
    # Indicado (quem foi indicado)
    referred_id = Column(BigInteger, nullable=False, unique=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_deposit_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Affiliate(id={self.id}, referrer={self.referrer_id}, referred={self.referred_id})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "referrer_id": self.referrer_id,
            "referred_id": self.referred_id,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }


class AffiliateCommission(Base):
    """Comissão gerada por afiliado"""
    
    __tablename__ = "affiliate_commissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Afiliado que recebe
    affiliate_id = Column(BigInteger, nullable=False, index=True)
    
    # Indicado que gerou a comissão
    referred_id = Column(BigInteger, nullable=False)
    
    # Detalhes da comissão
    payment_id = Column(Integer, nullable=True)  # ID do pagamento que gerou
    deposit_amount = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)  # Percentual
    commission_amount = Column(Float, nullable=False)
    
    # Status
    status = Column(String(50), default="credited")  # pending, credited, cancelled
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadados
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AffiliateCommission(id={self.id}, affiliate={self.affiliate_id}, amount={self.commission_amount})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "affiliate_id": self.affiliate_id,
            "referred_id": self.referred_id,
            "payment_id": self.payment_id,
            "deposit_amount": self.deposit_amount,
            "commission_rate": self.commission_rate,
            "commission_amount": self.commission_amount,
            "status": self.status,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
