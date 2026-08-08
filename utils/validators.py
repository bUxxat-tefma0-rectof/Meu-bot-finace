"""
Utilitários de Validação
Valida dados de entrada do usuário e administrador
"""

import re
import json
import base64
from typing import Tuple, Optional, Union


# ===========================================
# VALIDAÇÕES GERAIS
# ===========================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Valida endereço de email
    
    Args:
        email: Email a validar
        
    Returns:
        (válido, mensagem de erro)
        
    Examples:
        >>> validate_email("user@example.com")
        (True, '')
        >>> validate_email("invalido")
        (False, 'Email inválido')
    """
    if not email:
        return False, "Email é obrigatório"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return True, ""
    
    return False, "Email inválido"


def validate_pix_value(value: float, min_value: float = 30.0, max_value: float = 1000.0) -> Tuple[bool, str]:
    """
    Valida valor de recarga PIX
    
    Args:
        value: Valor a validar
        min_value: Valor mínimo
        max_value: Valor máximo
        
    Returns:
        (válido, mensagem)
    """
    if not isinstance(value, (int, float)):
        return False, "Valor deve ser numérico"
    
    if value <= 0:
        return False, "Valor deve ser positivo"
    
    if value < min_value:
        return False, f"Valor mínimo: R$ {min_value:.2f}"
    
    if value > max_value:
        return False, f"Valor máximo: R$ {max_value:.2f}"
    
    # Verifica duas casas decimais no máximo
    if round(value, 2) != value:
        return False, "Máximo de 2 casas decimais"
    
    return True, ""


def validate_telegram_id(telegram_id: Union[int, str]) -> Tuple[bool, str]:
    """
    Valida ID do Telegram
    
    Args:
        telegram_id: ID a validar
        
    Returns:
        (válido, mensagem)
    """
    try:
        tid = int(telegram_id)
        
        if tid <= 0:
            return False, "ID deve ser positivo"
        
        if tid > 9999999999:
            return False, "ID muito grande"
        
        return True, ""
    except (ValueError, TypeError):
        return False, "ID inválido"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Valida URL
    
    Args:
        url: URL a validar
        
    Returns:
        (válido, mensagem)
    """
    if not url:
        return False, "URL é obrigatória"
    
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    
    if re.match(pattern, url):
        return True, ""
    
    return False, "URL inválida"


def validate_product_price(price: Union[float, str]) -> Tuple[bool, str]:
    """
    Valida preço de produto
    
    Args:
        price: Preço a validar
        
    Returns:
        (válido, mensagem)
    """
    try:
        price_float = float(price)
        
        if price_float <= 0:
            return False, "Preço deve ser maior que zero"
        
        if price_float > 99999.99:
            return False, "Preço muito alto (máx: R$ 99.999,99)"
        
        if round(price_float, 2) != price_float:
            return False, "Máximo de 2 casas decimais"
        
        return True, ""
    except (ValueError, TypeError):
        return False, "Preço inválido"


def validate_stock_code(code: str) -> Tuple[bool, str]:
    """
    Valida código de item de estoque
    
    Args:
        code: Código a validar
        
    Returns:
        (válido, mensagem)
    """
    if not code:
        return False, "Código é obrigatório"
    
    if len(code) < 3:
        return False, "Código muito curto (mín: 3 caracteres)"
    
    if len(code) > 500:
        return False, "Código muito longo (máx: 500 caracteres)"
    
    # Verifica caracteres perigosos
    dangerous = ['<', '>', '"', "'", ';', '--', '/*', '*/']
    for char in dangerous:
        if char in code:
            return False, f"Código contém caracteres inválidos: {char}"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Valida nome de usuário
    
    Args:
        username: Username a validar
        
    Returns:
        (válido, mensagem)
    """
    if not username:
        return True, ""  # Opcional
    
    if len(username) < 3:
        return False, "Username muito curto (mín: 3)"
    
    if len(username) > 32:
        return False, "Username muito longo (máx: 32)"
    
    pattern = r'^[a-zA-Z0-9_]+$'
    
    if re.match(pattern, username):
        return True, ""
    
    return False, "Username deve conter apenas letras, números e underscore"


# ===========================================
# VALIDAÇÕES BRASILEIRAS
# ===========================================

def validate_brazilian_phone(phone: str) -> Tuple[bool, str]:
    """
    Valida telefone brasileiro
    
    Args:
        phone: Número de telefone
        
    Returns:
        (válido, mensagem)
    """
    if not phone:
        return False, "Telefone é obrigatório"
    
    # Remove máscara
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) not in [10, 11]:
        return False, "Telefone deve ter 10 ou 11 dígitos"
    
    # Verifica DDD
    ddd = int(digits[:2])
    valid_ddds = [
        11, 12, 13, 14, 15, 16, 17, 18, 19,  # SP
        21, 22, 24,  # RJ
        27, 28,  # ES
        31, 32, 33, 34, 35, 37, 38,  # MG
        41, 42, 43, 44, 45, 46,  # PR
        47, 48, 49,  # SC
        51, 53, 54, 55,  # RS
        61,  # DF
        62, 64,  # GO
        63,  # TO
        65, 66,  # MT
        67,  # MS
        68,  # AC
        69,  # RO
        71, 73, 74, 75, 77,  # BA
        79,  # SE
        81, 87,  # PE
        82,  # AL
        83,  # PB
        84,  # RN
        85, 88,  # CE
        86, 89,  # PI
        91, 93, 94,  # PA
        92, 97,  # AM
        95,  # RR
        96,  # AP
        98, 99,  # MA
    ]
    
    if ddd not in valid_ddds:
        return False, "DDD inválido"
    
    # Celular deve começar com 9
    if len(digits) == 11 and digits[2] != '9':
        return False, "Celular deve começar com 9"
    
    return True, ""


def validate_cpf(cpf: str) -> Tuple[bool, str]:
    """
    Valida CPF (algoritmo oficial)
    
    Args:
        cpf: CPF a validar
        
    Returns:
        (válido, mensagem)
    """
    if not cpf:
        return False, "CPF é obrigatório"
    
    # Remove máscara
    digits = re.sub(r'\D', '', cpf)
    
    if len(digits) != 11:
        return False, "CPF deve ter 11 dígitos"
    
    # Verifica se todos são iguais
    if len(set(digits)) == 1:
        return False, "CPF inválido"
    
    # Validação do primeiro dígito
    sum_val = sum(int(digits[i]) * (10 - i) for i in range(9))
    digit1 = (sum_val * 10) % 11
    if digit1 == 10:
        digit1 = 0
    
    if int(digits[9]) != digit1:
        return False, "CPF inválido"
    
    # Validação do segundo dígito
    sum_val = sum(int(digits[i]) * (11 - i) for i in range(10))
    digit2 = (sum_val * 10) % 11
    if digit2 == 10:
        digit2 = 0
    
    if int(digits[10]) != digit2:
        return False, "CPF inválido"
    
    return True, ""


def validate_cnpj(cnpj: str) -> Tuple[bool, str]:
    """
    Valida CNPJ (algoritmo oficial)
    
    Args:
        cnpj: CNPJ a validar
        
    Returns:
        (válido, mensagem)
    """
    if not cnpj:
        return False, "CNPJ é obrigatório"
    
    digits = re.sub(r'\D', '', cnpj)
    
    if len(digits) != 14:
        return False, "CNPJ deve ter 14 dígitos"
    
    if len(set(digits)) == 1:
        return False, "CNPJ inválido"
    
    # Validação
    def calc_digit(cnpj_part, weights):
        total = sum(int(d) * w for d, w in zip(cnpj_part, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    digit1 = calc_digit(digits[:12], weights1)
    digit2 = calc_digit(digits[:13], weights2)
    
    if int(digits[12]) == digit1 and int(digits[13]) == digit2:
        return True, ""
    
    return False, "CNPJ inválido"


def validate_pix_key(key: str) -> Tuple[bool, str]:
    """
    Valida chave PIX
    
    Args:
        key: Chave PIX
        
    Returns:
        (válido, mensagem)
    """
    if not key:
        return False, "Chave PIX é obrigatória"
    
    # Email
    if '@' in key:
        return validate_email(key)
    
    # CPF
    digits = re.sub(r'\D', '', key)
    if len(digits) == 11:
        return validate_cpf(key)
    
    # CNPJ
    if len(digits) == 14:
        return validate_cnpj(key)
    
    # Celular
    if '+' in key or len(digits) >= 10:
        return validate_brazilian_phone(key)
    
    # Chave aleatória (UUID)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, key, re.IGNORECASE):
        return True, ""
    
    return False, "Chave PIX inválida"


# ===========================================
# VALIDAÇÕES DO SISTEMA
# ===========================================

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Valida força da senha
    
    Args:
        password: Senha
        
    Returns:
        (válido, mensagem)
    """
    if not password:
        return False, "Senha é obrigatória"
    
    if len(password) < 8:
        return False, "Senha deve ter no mínimo 8 caracteres"
    
    if len(password) > 128:
        return False, "Senha muito longa (máx: 128)"
    
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter maiúscula"
    
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter minúscula"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter caractere especial"
    
    return True, ""


def validate_discount_code(code: str) -> Tuple[bool, str]:
    """
    Valida código de desconto
    
    Args:
        code: Código
        
    Returns:
        (válido, mensagem)
    """
    if not code:
        return False, "Código é obrigatório"
    
    if len(code) < 3:
        return False, "Código muito curto"
    
    if len(code) > 20:
        return False, "Código muito longo"
    
    if not re.match(r'^[A-Z0-9_-]+$', code, re.IGNORECASE):
        return False, "Código deve conter apenas letras, números, - e _"
    
    return True, ""


def validate_category_name(name: str) -> Tuple[bool, str]:
    """
    Valida nome de categoria
    
    Args:
        name: Nome
        
    Returns:
        (válido, mensagem)
    """
    if not name:
        return False, "Nome é obrigatório"
    
    if len(name) < 2:
        return False, "Nome muito curto (mín: 2)"
    
    if len(name) > 100:
        return False, "Nome muito longo (máx: 100)"
    
    return True, ""


def validate_product_name(name: str) -> Tuple[bool, str]:
    """
    Valida nome de produto
    
    Args:
        name: Nome
        
    Returns:
        (válido, mensagem)
    """
    if not name:
        return False, "Nome é obrigatório"
    
    if len(name) < 2:
        return False, "Nome muito curto (mín: 2)"
    
    if len(name) > 200:
        return False, "Nome muito longo (máx: 200)"
    
    return True, ""


# ===========================================
# VALIDAÇÕES DE FORMATO
# ===========================================

def is_valid_json(text: str) -> bool:
    """
    Verifica se string é JSON válido
    
    Args:
        text: String a verificar
        
    Returns:
        É JSON válido
    """
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def is_valid_base64(text: str) -> bool:
    """
    Verifica se string é Base64 válido
    
    Args:
        text: String a verificar
        
    Returns:
        É Base64 válido
    """
    try:
        base64.b64decode(text, validate=True)
        return True
    except Exception:
        return False


def is_valid_hex_color(color: str) -> bool:
    """
    Verifica se é cor hexadecimal válida
    
    Args:
        color: Cor (#RGB, #RRGGBB)
        
    Returns:
        É cor válida
    """
    pattern = r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$'
    return bool(re.match(pattern, color))
