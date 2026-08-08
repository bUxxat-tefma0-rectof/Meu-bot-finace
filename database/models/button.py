"""
Modelo de Botões do Menu
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text
)

from database.connection import Base


class Button(Base):
    """Botão customizável do menu"""
    
    __tablename__ = "buttons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação
    name = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)  # Texto visível
    emoji = Column(String(10), nullable=True)
    
    # Ação
    action = Column(String(100), nullable=False)  # Tipo de ação
    action_data = Column(Text, nullable=True)  # Dados da ação (link, comando, etc)
    
    # Posicionamento
    position = Column(Integer, default=0)
    row = Column(Integer, default=0)  # Linha no teclado
    parent_menu = Column(String(100), default="main")  # Menu pai
    
    # Status
    is_active = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    
    # Metadados
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Button(id={self.id}, name={self.name}, label={self.label})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "emoji": self.emoji,
            "action": self.action,
            "action_data": self.action_data,
            "position": self.position,
            "row": self.row,
            "parent_menu": self.parent_menu,
            "is_active": self.is_active,
            "is_visible": self.is_visible,
        }
