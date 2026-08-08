"""
Modelo de Pagamentos e Transações PIX
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, Float, String, 
    Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Payment(Base):
    """Pagamento/Recarga de saldo"""
    
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Detalhes do pagamento
    amount = Column(Float, nullable=False)
    provider = Column(String(50), default="pix")  # pix, manual
    status = Column(String(50), default="pending")  # pending, approved, expired, cancelled
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Metadados
    external_id = Column(String(200), nullable=True)  # ID na API externa
    notes = Column(Text, nullable=True)
    approved_by = Column(Integer, nullable=True)  # Admin ID (se manual)
    
    # Relacionamentos
    user = relationship("User", back_populates="payments")
    pix_transaction = relationship("PixTransaction", back_populates="payment", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "provider": self.provider,
            "status": self.status,
            "external_id": self.external_id,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "approved_at": self.approved_at.strftime("%d/%m/%Y %H:%M") if self.approved_at else None,
            "expires_at": self.expires_at.strftime("%d/%m/%Y %H:%M") if self.expires_at else None,
        }


class PixTransaction(Base):
    """Transação PIX específica"""
    
    __tablename__ = "pix_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Dados do PIX
    pix_code = Column(Text, nullable=True)  # Código copia e cola
    qr_code_base64 = Column(Text, nullable=True)  # QR Code em base64
    qr_code_file_id = Column(String(300), nullable=True)  # File ID do Telegram
    transaction_id = Column(String(200), nullable=True)  # ID da transação externa
    
    # Status
    webhook_received = Column(Boolean, default=False)
    webhook_data = Column(Text, nullable=True)  # JSON do webhook
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_check = Column(DateTime, nullable=True)
    
    # Relacionamentos
    payment = relationship("Payment", back_populates="pix_transaction")
    
    def __repr__(self):
        return f"<PixTransaction(id={self.id}, payment_id={self.payment_id})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "pix_code": self.pix_code,
            "transaction_id": self.transaction_id,
            "webhook_received": self.webhook_received,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
