"""
Utilitários de Formatação
Formata dados para exibição no bot e painel
"""

import re
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Union


# ===========================================
# FORMATAÇÃO DE MOEDA E NÚMEROS
# ===========================================

def format_currency(value: Union[int, float], symbol: bool = True) -> str:
    """
    Formata valor monetário
    
    Args:
        value: Valor numérico
        symbol: Incluir R$
        
    Returns:
        String formatada: "R$ 1.234,56" ou "1.234,56"
        
    Examples:
        >>> format_currency(1234.56)
        'R$ 1.234,56'
        >>> format_currency(99.9, symbol=False)
        '99,90'
    """
    if value is None:
        value = 0
    
    # Formata com 2 casas decimais
    formatted = f"{abs(value):,.2f}"
    
    # Substitui separadores para padrão brasileiro
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Adiciona símbolo
    prefix = "R$ " if symbol else ""
    sign = "-" if value < 0 else ""
    
    return f"{sign}{prefix}{formatted}"


def format_number(value: Union[int, float], decimals: int = 0) -> str:
    """
    Formata número com separadores
    
    Args:
        value: Número
        decimals: Casas decimais
        
    Returns:
        Número formatado
        
    Examples:
        >>> format_number(1234567)
        '1.234.567'
        >>> format_number(1234.56, 2)
        '1.234,56'
    """
    if value is None:
        value = 0
    
    if decimals > 0:
        formatted = f"{value:,.{decimals}f}"
    else:
        formatted = f"{int(value):,}"
    
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formata percentual
    
    Args:
        value: Valor (0.1 = 10%)
        decimals: Casas decimais
        
    Returns:
        String formatada: "10,0%"
    """
    percentage = value * 100
    return f"{percentage:.{decimals}f}%".replace(".", ",")


# ===========================================
# FORMATAÇÃO DE DATA E HORA
# ===========================================

def format_date(date: datetime, format_str: str = "%d/%m/%Y") -> str:
    """
    Formata data
    
    Args:
        date: Objeto datetime
        format_str: Formato desejado
        
    Returns:
        Data formatada
        
    Examples:
        >>> format_date(datetime(2024, 1, 15))
        '15/01/2024'
    """
    if not date:
        return "N/A"
    
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date)
        except ValueError:
            return date
    
    return date.strftime(format_str)


def format_datetime(dt: datetime) -> str:
    """
    Formata data e hora completa
    
    Args:
        dt: Data e hora
        
    Returns:
        String: "15/01/2024 14:30"
    """
    return format_date(dt, "%d/%m/%Y %H:%M")


def format_time_ago(dt: datetime) -> str:
    """
    Formata tempo relativo (ex: "há 5 minutos")
    
    Args:
        dt: Data/hora no passado
        
    Returns:
        String descritiva
        
    Examples:
        >>> format_time_ago(datetime.now() - timedelta(minutes=5))
        'há 5 minutos'
    """
    if not dt:
        return "N/A"
    
    now = datetime.utcnow()
    
    # Se dt for timezone-aware e now não, converte
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    
    diff = now - dt
    
    if diff.total_seconds() < 0:
        return "agora mesmo"
    
    minutes = int(diff.total_seconds() / 60)
    hours = minutes // 60
    days = diff.days
    
    if minutes < 1:
        return "agora mesmo"
    elif minutes == 1:
        return "há 1 minuto"
    elif minutes < 60:
        return f"há {minutes} minutos"
    elif hours == 1:
        return "há 1 hora"
    elif hours < 24:
        return f"há {hours} horas"
    elif days == 1:
        return "há 1 dia"
    elif days < 7:
        return f"há {days} dias"
    elif days < 30:
        semanas = days // 7
        return f"há {semanas} {'semana' if semanas == 1 else 'semanas'}"
    elif days < 365:
        meses = days // 30
        return f"há {meses} {'mês' if meses == 1 else 'meses'}"
    else:
        anos = days // 365
        return f"há {anos} {'ano' if anos == 1 else 'anos'}"


def format_countdown(seconds: int) -> str:
    """
    Formata contagem regressiva
    
    Args:
        seconds: Segundos restantes
        
    Returns:
        String: "05:30" ou "01:30:00"
    """
    if seconds <= 0:
        return "Expirado"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


# ===========================================
# FORMATAÇÃO DE TEXTO
# ===========================================

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Trunca texto com limite
    
    Args:
        text: Texto original
        max_length: Tamanho máximo
        suffix: Sufixo para indicar truncamento
        
    Returns:
        Texto truncado
        
    Examples:
        >>> truncate_text("Texto muito longo aqui", 10)
        'Texto muit...'
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def mask_pix_code(pix_code: str, visible_chars: int = 20) -> str:
    """
    Mascara código PIX para exibição segura
    
    Args:
        pix_code: Código PIX completo
        visible_chars: Quantos caracteres mostrar no início
        
    Returns:
        Código mascarado
    """
    if not pix_code or len(pix_code) <= visible_chars:
        return pix_code or ""
    
    return pix_code[:visible_chars] + "..." + pix_code[-10:]


def format_phone(phone: str) -> str:
    """
    Formata número de telefone brasileiro
    
    Args:
        phone: Número (com ou sem máscara)
        
    Returns:
        Número formatado: "(11) 99999-9999"
    """
    if not phone:
        return ""
    
    # Remove tudo que não for número
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 11:  # Celular com DDD
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:  # Fixo com DDD
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    elif len(digits) == 9:  # Celular sem DDD
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) == 8:  # Fixo sem DDD
        return f"{digits[:4]}-{digits[4:]}"
    
    return phone


def format_cpf(cpf: str) -> str:
    """
    Formata CPF
    
    Args:
        cpf: Números do CPF
        
    Returns:
        CPF formatado: "123.456.789-00"
    """
    if not cpf:
        return ""
    
    digits = re.sub(r'\D', '', cpf)
    
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    
    return cpf


def format_card_number(card_number: str) -> str:
    """
    Formata número de cartão (mascarado)
    
    Args:
        card_number: Número do cartão
        
    Returns:
        Número mascarado: "**** **** **** 1234"
    """
    if not card_number:
        return ""
    
    digits = re.sub(r'\D', '', card_number)
    
    if len(digits) >= 4:
        return f"**** **** **** {digits[-4:]}"
    
    return card_number


def sanitize_html(text: str) -> str:
    """
    Remove tags HTML perigosas
    
    Args:
        text: Texto com possível HTML
        
    Returns:
        Texto sanitizado
    """
    if not text:
        return ""
    
    # Remove tags perigosas
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
    
    for tag in dangerous_tags:
        text = re.sub(f'<{tag}.*?>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(f'<{tag}.*?/>', '', text, flags=re.IGNORECASE)
    
    # Remove atributos on* (event handlers)
    text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    return text


def escape_markdown(text: str, version: int = 2) -> str:
    """
    Escapa caracteres especiais do Markdown do Telegram
    
    Args:
        text: Texto original
        version: Versão do Markdown (1 ou 2)
        
    Returns:
        Texto escapado
    """
    if not text:
        return ""
    
    if version == 2:
        # MarkdownV2: caracteres especiais
        special_chars = r'_*[]()~`>#+-=|{}.!'
        escape_char = '\\'
    else:
        # MarkdownV1
        special_chars = r'_*`['
        escape_char = '\\'
    
    for char in special_chars:
        text = text.replace(char, escape_char + char)
    
    return text


def generate_random_code(length: int = 8, uppercase: bool = True) -> str:
    """
    Gera código aleatório
    
    Args:
        length: Tamanho do código
        uppercase: Apenas maiúsculas
        
    Returns:
        Código gerado
    """
    chars = string.ascii_uppercase + string.digits if uppercase else string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def format_file_size(size_bytes: int) -> str:
    """
    Formata tamanho de arquivo
    
    Args:
        size_bytes: Tamanho em bytes
        
    Returns:
        Tamanho formatado: "1.5 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def pluralize(count: int, singular: str, plural: str = None) -> str:
    """
    Retorna singular ou plural
    
    Args:
        count: Quantidade
        singular: Palavra no singular
        plural: Palavra no plural (opcional, adiciona 's')
        
    Returns:
        Palavra correta
        
    Examples:
        >>> pluralize(1, "produto")
        'produto'
        >>> pluralize(5, "produto")
        'produtos'
    """
    if count == 1:
        return singular
    
    if plural:
        return plural
    
    return singular + "s"


def format_table_row(columns: list, widths: list, align: str = "left") -> str:
    """
    Formata uma linha de tabela
    
    Args:
        columns: Valores das colunas
        widths: Larguras das colunas
        align: Alinhamento ('left', 'right', 'center')
        
    Returns:
        Linha formatada
    """
    row = ""
    
    for i, (col, width) in enumerate(zip(columns, widths)):
        col_str = str(col)
        
        if align == "right":
            row += col_str.rjust(width)
        elif align == "center":
            row += col_str.center(width)
        else:
            row += col_str.ljust(width)
        
        if i < len(columns) - 1:
            row += " │ "
    
    return row


def format_progress_bar(current: int, total: int, length: int = 20) -> str:
    """
    Cria barra de progresso
    
    Args:
        current: Valor atual
        total: Valor total
        length: Comprimento da barra
        
    Returns:
        Barra: "████████░░░░░░░░░░░░ 40%"
    """
    if total == 0:
        return "░░" * length + " 0%"
    
    percentage = min(current / total, 1.0)
    filled = int(length * percentage)
    bar = "█" * filled + "░" * (length - filled)
    
    return f"{bar} {percentage * 100:.0f}%"
