"""
Modelo de Configurações do Sistema
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime
)

from database.connection import Base


class SystemSetting(Base):
    """Configuração do sistema (chave-valor)"""
    
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Chave única
    key = Column(String(100), unique=True, nullable=False, index=True)
    
    # Valor
    value = Column(Text, nullable=True)
    
    # Tipo para validação
    value_type = Column(String(50), default="string")  # string, integer, float, boolean, json
    
    # Descrição
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")  # general, pix, notifications, etc
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SystemSetting(key={self.key}, value={self.value})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "description": self.description,
            "category": self.category,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M") if self.updated_at else None,
        }
