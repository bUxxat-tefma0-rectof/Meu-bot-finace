"""
Modelo de Sessão do Usuário no Bot
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship

from database.connection import Base


class UserSession(Base):
    """Sessão/Estado do usuário no bot"""
    
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Estado atual
    current_state = Column(String(100), nullable=True)  # Estado na conversação
    current_menu = Column(String(100), nullable=True)
    
    # Dados temporários
    temp_data = Column(Text, nullable=True)  # JSON com dados da sessão
    
    # Mensagens para limpeza
    message_ids = Column(Text, nullable=True)  # JSON com IDs de mensagens
    
    # Datas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, state={self.current_state})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "current_state": self.current_state,
            "current_menu": self.current_menu,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
            "last_activity": self.last_activity.strftime("%d/%m/%Y %H:%M") if self.last_activity else None,
        }
