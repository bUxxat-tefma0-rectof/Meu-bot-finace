"""
Utilitários de Segurança
Criptografia, tokens, sanitização e proteção de dados
"""

import os
import re
import hmac
import json
import time
import uuid
import base64
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)

# Chave de criptografia (32 bytes para AES-256)
ENCRYPTION_KEY = settings.ENCRYPTION_KEY.encode() if settings.ENCRYPTION_KEY else os.urandom(32)

# Cache para rate limiting
_rate_limit_cache: Dict[str, list] = {}


# ===========================================
# HASH E VERIFICAÇÃO
# ===========================================

def hash_data(data: str, algorithm: str = "sha256") -> str:
    """
    Gera hash de dados
    
    Args:
        data: Dados para hash
        algorithm: Algoritmo (sha256, sha512, md5)
        
    Returns:
        Hash hexadecimal
    """
    if not data:
        return ""
    
    hash_func = getattr(hashlib, algorithm, hashlib.sha256)
    
    # Adiciona salt para segurança extra
    salted = f"{data}:{settings.ENCRYPTION_KEY}"
    
    return hash_func(salted.encode()).hexdigest()


def verify_hash(data: str, hash_value: str, algorithm: str = "sha256") -> bool:
    """
    Verifica hash
    
    Args:
        data: Dados originais
        hash_value: Hash a verificar
        algorithm: Algoritmo
        
    Returns:
        Hash corresponde
    """
    return secure_compare(hash_data(data, algorithm), hash_value)


# ===========================================
# CRIPTOGRAFIA
# ===========================================

def encrypt_data(data: str) -> str:
    """
    Criptografa dados com AES-256
    
    Args:
        data: Dados a criptografar
        
    Returns:
        Dados criptografados em base64
    """
    try:
        from cryptography.fernet import Fernet
        
        # Deriva chave do Fernet a partir da chave de 32 bytes
        key = base64.urlsafe_b64encode(ENCRYPTION_KEY[:32].ljust(32, b'\0'))
        fernet = Fernet(key)
        
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
        
    except ImportError:
        # Fallback simples se cryptography não estiver disponível
        logger.warning("Cryptography não instalado, usando codificação simples")
        return base64.b64encode(data.encode()).decode()
    except Exception as e:
        logger.error(f"Erro ao criptografar: {e}")
        return data


def decrypt_data(encrypted_data: str) -> str:
    """
    Descriptografa dados
    
    Args:
        encrypted_data: Dados criptografados
        
    Returns:
        Dados originais
    """
    try:
        from cryptography.fernet import Fernet
        
        key = base64.urlsafe_b64encode(ENCRYPTION_KEY[:32].ljust(32, b'\0'))
        fernet = Fernet(key)
        
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
        
    except ImportError:
        try:
            return base64.b64decode(encrypted_data.encode()).decode()
        except Exception:
            return encrypted_data
    except Exception as e:
        logger.error(f"Erro ao descriptografar: {e}")
        return encrypted_data


# ===========================================
# TOKENS
# ===========================================

def generate_token(length: int = 32) -> str:
    """
    Gera token seguro
    
    Args:
        length: Tamanho do token em bytes
        
    Returns:
        Token hexadecimal
    """
    return secrets.token_hex(length)


def generate_secure_id() -> str:
    """
    Gera ID único seguro
    
    Returns:
        UUID v4
    """
    return str(uuid.uuid4())


def validate_token(token: str, stored_token: str, max_age: int = 3600) -> bool:
    """
    Valida token com tempo de expiração
    
    Args:
        token: Token recebido
        stored_token: Token armazenado (pode conter timestamp)
        max_age: Idade máxima em segundos
        
    Returns:
        Token válido
    """
    if not token or not stored_token:
        return False
    
    # Verifica comparação segura
    if not secure_compare(token, stored_token):
        return False
    
    # Se o token armazenado tem timestamp, verifica idade
    if ":" in stored_token:
        try:
            token_time = int(stored_token.split(":")[-1])
            if time.time() - token_time > max_age:
                return False
        except (ValueError, IndexError):
            pass
    
    return True


# ===========================================
# SANITIZAÇÃO
# ===========================================

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitiza entrada do usuário
    
    Args:
        text: Texto a sanitizar
        max_length: Tamanho máximo
        
    Returns:
        Texto sanitizado
    """
    if not text:
        return ""
    
    # Limita tamanho
    text = text[:max_length]
    
    # Remove caracteres nulos
    text = text.replace('\x00', '')
    
    # Remove caracteres de controle (exceto quebras de linha e tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Remove tags HTML
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def mask_sensitive_data(data: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """
    Mascara dados sensíveis
    
    Args:
        data: Dado original
        visible_start: Caracteres visíveis no início
        visible_end: Caracteres visíveis no final
        
    Returns:
        Dado mascarado
        
    Examples:
        >>> mask_sensitive_data("1234567890", 3, 3)
        '123****890'
    """
    if not data:
        return ""
    
    length = len(data)
    
    if length <= visible_start + visible_end:
        return "*" * length
    
    start = data[:visible_start]
    end = data[-visible_end:] if visible_end > 0 else ""
    middle = "*" * (length - visible_start - visible_end)
    
    return f"{start}{middle}{end}"


# ===========================================
# COMPARAÇÃO SEGURA
# ===========================================

def secure_compare(a: str, b: str) -> bool:
    """
    Comparação timing-attack safe
    
    Args:
        a: Primeiro valor
        b: Segundo valor
        
    Returns:
        São iguais
    """
    return hmac.compare_digest(
        a.encode() if isinstance(a, str) else a,
        b.encode() if isinstance(b, str) else b,
    )


# ===========================================
# RATE LIMITING
# ===========================================

def rate_limit_check(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """
    Verifica rate limiting
    
    Args:
        key: Identificador único (ex: user_id:action)
        max_requests: Máximo de requisições
        window_seconds: Janela de tempo em segundos
        
    Returns:
        (permitido, tentativas restantes)
    """
    now = time.time()
    cutoff = now - window_seconds
    
    # Limpa entradas antigas
    if key in _rate_limit_cache:
        _rate_limit_cache[key] = [
            ts for ts in _rate_limit_cache[key] if ts > cutoff
        ]
    else:
        _rate_limit_cache[key] = []
    
    # Verifica limite
    current_requests = len(_rate_limit_cache[key])
    
    if current_requests >= max_requests:
        return False, 0
    
    # Registra requisição
    _rate_limit_cache[key].append(now)
    
    remaining = max_requests - current_requests - 1
    
    return True, remaining


def clear_rate_limit_cache():
    """Limpa cache de rate limiting expirado"""
    now = time.time()
    
    for key in list(_rate_limit_cache.keys()):
        _rate_limit_cache[key] = [
            ts for ts in _rate_limit_cache[key]
            if now - ts < 300  # Mantém últimos 5 minutos
        ]
        
        if not _rate_limit_cache[key]:
            del _rate_limit_cache[key]


# ===========================================
# ASSINATURA DE DADOS
# ===========================================

def validate_signature(
    payload: str,
    signature: str,
    secret: str = None,
    algorithm: str = "sha256",
) -> bool:
    """
    Valida assinatura HMAC
    
    Args:
        payload: Dados assinados
        signature: Assinatura recebida
        secret: Chave secreta
        algorithm: Algoritmo de hash
        
    Returns:
        Assinatura válida
    """
    if not secret:
        secret = settings.ENCRYPTION_KEY
    
    if not payload or not signature:
        return False
    
    hash_func = getattr(hashlib, algorithm, hashlib.sha256)
    
    expected = hmac.new(
        secret.encode() if isinstance(secret, str) else secret,
        payload.encode() if isinstance(payload, str) else payload,
        hash_func,
    ).hexdigest()
    
    return secure_compare(expected, signature)


# ===========================================
# CSRF PROTECTION
# ===========================================

_csrf_tokens: Dict[str, dict] = {}


def generate_csrf_token(session_id: str) -> str:
    """
    Gera token CSRF
    
    Args:
        session_id: ID da sessão
        
    Returns:
        Token CSRF
    """
    token = secrets.token_hex(32)
    expires = time.time() + 3600  # 1 hora
    
    _csrf_tokens[session_id] = {
        "token": token,
        "expires": expires,
    }
    
    return token


def validate_csrf_token(session_id: str, token: str) -> bool:
    """
    Valida token CSRF
    
    Args:
        session_id: ID da sessão
        token: Token CSRF
        
    Returns:
        Token válido
    """
    stored = _csrf_tokens.get(session_id)
    
    if not stored:
        return False
    
    if time.time() > stored["expires"]:
        del _csrf_tokens[session_id]
        return False
    
    if not secure_compare(stored["token"], token):
        return False
    
    # Token de uso único - remove após validação
    del _csrf_tokens[session_id]
    
    return True


# ===========================================
# PROTEÇÃO DE DADOS
# ===========================================

def generate_api_key() -> str:
    """
    Gera chave de API segura
    
    Returns:
        Chave de API
    """
    prefix = "gcs_"  # Gift Card Store
    random_part = secrets.token_hex(24)
    return f"{prefix}{random_part}"


def secure_random_int(min_val: int = 0, max_val: int = 999999) -> int:
    """
    Gera número aleatório seguro
    
    Args:
        min_val: Valor mínimo
        max_val: Valor máximo
        
    Returns:
        Número aleatório
    """
    return secrets.randbelow(max_val - min_val + 1) + min_val


def hash_password(password: str) -> Tuple[str, str]:
    """
    Gera hash de senha com salt
    
    Args:
        password: Senha em texto puro
        
    Returns:
        (hash, salt)
    """
    salt = secrets.token_hex(16)
    
    # PBKDF2 com 100k iterações
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,
    )
    
    hash_str = hash_bytes.hex()
    
    return hash_str, salt


def verify_password(password: str, hash_str: str, salt: str) -> bool:
    """
    Verifica senha contra hash
    
    Args:
        password: Senha a verificar
        hash_str: Hash armazenado
        salt: Salt usado no hash
        
    Returns:
        Senha correta
    """
    new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,
    ).hex()
    
    return secure_compare(new_hash, hash_str)


# ===========================================
# LIMPEZA
# ===========================================

def secure_cleanup():
    """Limpa caches e dados temporários"""
    clear_rate_limit_cache()
    
    # Limpa CSRF tokens expirados
    now = time.time()
    for session_id in list(_csrf_tokens.keys()):
        if now > _csrf_tokens[session_id]["expires"]:
            del _csrf_tokens[session_id]
