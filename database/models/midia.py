"""
Modelo de Mídia (Imagens, Banners)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text
)

from database.connection import Base


class Media(Base):
    """Arquivo de mídia"""
    
    __tablename__ = "media"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação
    name = Column(String(200), nullable=False)
    file_id = Column(String(300), nullable=False, unique=True)  # File ID do Telegram
    file_type = Column(String(50), default="photo")  # photo, video, document, animation
    
    # Categoria da mídia
    media_category = Column(String(50), default="general")
    # product_image, category_image, banner, menu_image, campaign
    
    # Relacionamento
    related_id = Column(Integer, nullable=True)  # ID do item relacionado
    related_type = Column(String(50), nullable=True)  # product, category, etc
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadados
    file_size = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Media(id={self.id}, name={self.name}, type={self.file_type})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "file_id": self.file_id,
            "file_type": self.file_type,
            "media_category": self.media_category,
            "related_id": self.related_id,
            "related_type": self.related_type,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }
