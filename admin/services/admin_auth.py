"""
Serviço de autenticação do painel admin
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)


class AdminAuthService:
    """Gerencia autenticação e permissões de administradores"""
    
    def __init__(self):
        self.admin_sessions = {}
    
    async def authenticate(self, username: str, password: str) -> Optional[str]:
        """Autentica um administrador e retorna token de sessão"""
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            token = self._generate_token(username)
            self.admin_sessions[token] = {
                'username': username,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=24),
            }
            return token
        return None
    
    async def validate_token(self, token: str) -> bool:
        """Valida um token de sessão"""
        session = self.admin_sessions.get(token)
        if not session:
            return False
        
        if datetime.now() > session['expires_at']:
            del self.admin_sessions[token]
            return False
        
        return True
    
    async def logout(self, token: str):
        """Remove uma sessão"""
        self.admin_sessions.pop(token, None)
    
    def _generate_token(self, username: str) -> str:
        """Gera um token simples"""
        import hashlib
        import time
        
        raw = f"{username}:{time.time()}:{settings.ENCRYPTION_KEY}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    async def check_permission(self, user_id: int, permission: str) -> bool:
        """Verifica se um usuário tem permissão específica"""
        # Por enquanto, verifica apenas se é admin
        if not settings.is_admin(user_id):
            return False
        
        # Futuramente: verificar permissões granulares do banco
        admin_permissions = {
            'dashboard': True,
            'users': True,
            'products': True,
            'stock': True,
            'payments': True,
            'affiliates': True,
            'settings': True,
            'admins': True,
            'logs': True,
        }
        
        return admin_permissions.get(permission, False)
