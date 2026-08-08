"""
Modelo de Item de Estoque
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from database.connection import Base


class StockItem(Base):
    """Item individual no estoque"""
    
    __tablename__ = "stock_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Código do item
    code = Column(Text, nullable=False)
    
    # Status
    status = Column(String(50), default="available")  # available, reserved, sold, cancelled
    is_active = Column(Boolean, default=True)
    
    # Rastreamento de venda
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    sold_to = Column(Integer, nullable=True)  # Telegram ID do comprador
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sold_at = Column(DateTime, nullable=True)
    
    # Metadados
    added_by = Column(Integer, nullable=True)  # Admin ID
    notes = Column(Text, nullable=True)
    
    # Relacionamentos
    product = relationship("Product", back_populates="stock_items")
    order = relationship("Order", backref="stock_items_relation")
    
    def __repr__(self):
        return f"<StockItem(id={self.id}, product_id={self.product_id}, status={self.status})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "code": self.code,
            "status": self.status,
            "order_id": self.order_id,
            "sold_to": self.sold_to,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "sold_at": self.sold_at.strftime("%d/%m/%Y %H:%M") if self.sold_at else None,
        }
