"""
Modelo de Produto
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Product(Base):
    """Produto da loja"""
    
    __tablename__ = "products"
    
    # Identificação
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    # Preço e estoque
    price = Column(Float, nullable=False, default=0.0)
    stock_count = Column(Integer, default=0)
    
    # Conteúdo
    description = Column(Text, nullable=True)
    warranty = Column(String(100), default="7 dias")
    delivery_text = Column(Text, nullable=True)  # Texto de entrega com {codigo}
    delivery_type = Column(Integer, default=1)  # 1=texto único, 2=código individual
    
    # Marketing
    promotional_title = Column(String(200), nullable=True)
    position = Column(Integer, default=0)
    
    # Estatísticas
    total_sales = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)
    
    # Metadados
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    category = relationship("Category", back_populates="products")
    media_items = relationship("ProductMedia", back_populates="product", cascade="all, delete-orphan")
    stock_items = relationship("StockItem", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "price": self.price,
            "stock_count": self.stock_count,
            "description": self.description,
            "warranty": self.warranty,
            "delivery_text": self.delivery_text,
            "delivery_type": self.delivery_type,
            "promotional_title": self.promotional_title,
            "position": self.position,
            "total_sales": self.total_sales,
            "total_views": self.total_views,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "image_id": self.media_items[0].file_id if self.media_items else None,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }


class ProductMedia(Base):
    """Mídia do produto (imagens)"""
    
    __tablename__ = "product_media"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    file_id = Column(String(300), nullable=False)  # File ID do Telegram
    file_type = Column(String(50), default="photo")  # photo, video, document
    is_main = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    product = relationship("Product", back_populates="media_items")
    
    def __repr__(self):
        return f"<ProductMedia(id={self.id}, product_id={self.product_id})>"
