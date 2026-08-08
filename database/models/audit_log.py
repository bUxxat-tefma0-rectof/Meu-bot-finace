"""
Modelo de Logs de Auditoria
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Text
)

from database.connection import Base


class AuditLog(Base):
    """Registro de ações administrativas"""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Quem realizou a ação
    admin_id = Column(BigInteger, nullable=True)  # Telegram ID
    admin_name = Column(String(150), nullable=True)
    
    # Ação realizada
    action = Column(String(100), nullable=False)  # create, update, delete, etc
    entity_type = Column(String(50), nullable=False)  # user, product, stock, payment, etc
    entity_id = Column(Integer, nullable=True)
    
    # Detalhes
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)  # JSON
    new_value = Column(Text, nullable=True)  # JSON
    
    # Contexto
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "admin_name": self.admin_name,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
        }
