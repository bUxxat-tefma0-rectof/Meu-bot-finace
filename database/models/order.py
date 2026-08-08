"""
Modelo de Pedido/Compra
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Order(Base):
    """Pedido/Compra realizada"""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Detalhes da compra
    total_amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="balance")  # balance, pix
    
    # Status
    status = Column(String(50), default="completed")  # pending, completed, cancelled, refunded
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadados
    notes = Column(Text, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, total={self.total_amount})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "status": self.status,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "completed_at": self.completed_at.strftime("%d/%m/%Y %H:%M") if self.completed_at else None,
        }


class OrderItem(Base):
    """Item dentro de um pedido"""
    
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id", ondelete="SET NULL"), nullable=True)
    
    # Detalhes do item no momento da compra
    product_name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    delivery_content = Column(Text, nullable=True)  # Código ou texto entregue
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product={self.product_name})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "price": self.price,
            "delivery_content": self.delivery_content,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
