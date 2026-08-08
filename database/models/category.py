"""
Modelo de Categoria de Produtos
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Category(Base):
    """Categoria de produtos"""
    
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    emoji = Column(String(10), default="📦")
    description = Column(Text, nullable=True)
    
    # Mídia
    image_id = Column(String(300), nullable=True)  # File ID do Telegram
    
    # Ordenação e status
    position = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadados
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    products = relationship("Product", back_populates="category", lazy="dynamic")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "description": self.description,
            "image_id": self.image_id,
            "position": self.position,
            "is_active": self.is_active,
            "product_count": 0,  # Preenchido na query
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
