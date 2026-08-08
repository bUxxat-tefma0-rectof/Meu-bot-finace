"""
Modelo de Notificações
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, Text
)

from database.connection import Base


class Notification(Base):
    """Notificação enviada ao canal"""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Tipo de notificação
    type = Column(String(50), nullable=False, index=True)
    # purchase, new_stock, pix_approved, pix_expired, 
    # new_user, low_stock, product_sold_out, commission
    
    # Conteúdo
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    
    # Status
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Destino
    channel_id = Column(String(100), nullable=True)
    message_id = Column(Integer, nullable=True)  # ID da mensagem no Telegram
    
    # Relacionado a
    related_user_id = Column(BigInteger, nullable=True)
    related_product_id = Column(Integer, nullable=True)
    related_payment_id = Column(Integer, nullable=True)
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadados
    extra_data = Column(Text, nullable=True)  # JSON com dados extras
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, sent={self.is_sent})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "is_sent": self.is_sent,
            "sent_at": self.sent_at.strftime("%d/%m/%Y %H:%M") if self.sent_at else None,
            "channel_id": self.channel_id,
            "related_user_id": self.related_user_id,
            "related_product_id": self.related_product_id,
            "related_payment_id": self.related_payment_id,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
