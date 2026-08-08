"""
Modelo de Templates de Mensagens
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime
)

from database.connection import Base


class MessageTemplate(Base):
    """Template de mensagem do bot"""
    
    __tablename__ = "message_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação
    key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Conteúdo
    content = Column(Text, nullable=False)
    
    # Variáveis disponíveis (para documentação)
    available_variables = Column(Text, nullable=True)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<MessageTemplate(id={self.id}, key={self.key})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "available_variables": self.available_variables,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M") if self.updated_at else None,
        }
