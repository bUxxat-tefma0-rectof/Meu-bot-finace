"""
LOJA DE GIFTCARDS - Configurações do Sistema
Gerencia todas as configurações via variáveis de ambiente e banco de dados
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

class Settings:
    """Classe central de configurações do sistema"""
    
    # ===========================================
    # CONFIGURAÇÕES DO BOT
    # ===========================================
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "GiftcardStore_bot")
    
    # ===========================================
    # CONFIGURAÇÕES DO BANCO DE DADOS
    # ===========================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///giftcards.db"
    )
    
    # Para PostgreSQL no Render:
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    
    # ===========================================
    # CONFIGURAÇÕES DO CANAL OBRIGATÓRIO
    # ===========================================
    REQUIRED_CHANNEL_ID: str = os.getenv("REQUIRED_CHANNEL_ID", "")
    REQUIRED_CHANNEL_LINK: str = os.getenv("REQUIRED_CHANNEL_LINK", "https://t.me/seucanal")
    REQUIRED_CHANNEL_USERNAME: str = os.getenv("REQUIRED_CHANNEL_USERNAME", "@seucanal")
    
    # ===========================================
    # CONFIGURAÇÕES DE PIX E PAGAMENTOS
    # ===========================================
    PIX_MIN_VALUE: float = float(os.getenv("PIX_MIN_VALUE", "30.00"))
    PIX_MAX_VALUE: float = float(os.getenv("PIX_MAX_VALUE", "1000.00"))
    PIX_EXPIRATION_MINUTES: int = int(os.getenv("PIX_EXPIRATION_MINUTES", "30"))
    
    # API de pagamento (configurável via painel admin)
    PIX_PROVIDER: str = os.getenv("PIX_PROVIDER", "mercado_pago")  # ou "efi", "zendry", etc.
    PIX_API_URL: str = os.getenv("PIX_API_URL", "")
    PIX_API_KEY: str = os.getenv("PIX_API_KEY", "")
    PIX_CLIENT_ID: str = os.getenv("PIX_CLIENT_ID", "")
    PIX_CLIENT_SECRET: str = os.getenv("PIX_CLIENT_SECRET", "")
    PIX_WEBHOOK_URL: str = os.getenv("PIX_WEBHOOK_URL", "")
    PIX_ENVIRONMENT: str = os.getenv("PIX_ENVIRONMENT", "sandbox")  # "production" ou "sandbox"
    
    # ===========================================
    # CONFIGURAÇÕES DE AFILIADOS
    # ===========================================
    AFFILIATE_COMMISSION_PERCENT: float = float(os.getenv("AFFILIATE_COMMISSION_PERCENT", "10.0"))
    AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION: float = float(
        os.getenv("AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION", "30.00")
    )
    
    # ===========================================
    # CONFIGURAÇÕES DE SUPORTE
    # ===========================================
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@suporte")
    SUPPORT_LINK: str = os.getenv("SUPPORT_LINK", "https://t.me/suporte")
    
    # ===========================================
    # CONFIGURAÇÕES DE NOTIFICAÇÕES
    # ===========================================
    NOTIFICATION_CHANNEL_ID: str = os.getenv("NOTIFICATION_CHANNEL_ID", "")
    NOTIFICATION_CHANNEL_LINK: str = os.getenv("NOTIFICATION_CHANNEL_LINK", "@meucanal")
    
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
    
    # Notificações específicas (ativar/desativar)
    NOTIFY_ON_PURCHASE: bool = os.getenv("NOTIFY_ON_PURCHASE", "true").lower() == "true"
    NOTIFY_ON_NEW_STOCK: bool = os.getenv("NOTIFY_ON_NEW_STOCK", "true").lower() == "true"
    NOTIFY_ON_PIX_APPROVED: bool = os.getenv("NOTIFY_ON_PIX_APPROVED", "true").lower() == "true"
    NOTIFY_ON_PIX_EXPIRED: bool = os.getenv("NOTIFY_ON_PIX_EXPIRED", "false").lower() == "true"
    NOTIFY_ON_NEW_USER: bool = os.getenv("NOTIFY_ON_NEW_USER", "true").lower() == "true"
    NOTIFY_ON_LOW_STOCK: bool = os.getenv("NOTIFY_ON_LOW_STOCK", "true").lower() == "true"
    NOTIFY_ON_COMMISSION: bool = os.getenv("NOTIFY_ON_COMMISSION", "true").lower() == "true"
    
    # Limite para alerta de estoque baixo
    LOW_STOCK_THRESHOLD: int = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))
    
    # ===========================================
    # CONFIGURAÇÕES DE SEGURANÇA
    # ===========================================
    ADMIN_IDS: list = [
        int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_
    ]
    
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "sua_chave_secreta_aqui_32_caracteres")
    
    # ===========================================
    # CONFIGURAÇÕES DE MENSAGENS PADRÃO
    # ===========================================
    MESSAGES: Dict[str, str] = {
        # Mensagem de boas-vindas (após verificação do canal)
        "WELCOME_MESSAGE": (
            "Olá, Bem-vindo a LOJA DE GIFTCARDS 👋🎁\n"
            "🆔 𝗦𝗲𝘂 𝗜𝗗: {telegram_id}\n"
            "💰 𝗦𝗮𝗹𝗱𝗼 𝗔𝘁𝘂𝗮𝗹: R$ {saldo}\n"
            "🛒 𝗖𝗼𝗺𝗽𝗿𝗮𝘀 𝗥𝗲𝗮𝗹𝗶𝘇𝗮𝗱𝗮𝘀: {compras}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ REGRAS IMPORTANTES\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "• 🕐 Prazo de 15 minutos para resgatar o gift card após a compra.\n"
            "• ✅ Garantimos que o saldo será creditado em sua conta.\n"
            "• 💬 Não sabe usar? Toque em \"Suporte\".\n"
            "• 🆕 Novos gift cards são adicionados diariamente.\n"
            "• 📦 Não temos previsão de reposição.\n"
            "• 💰 Quer ganhar saldo grátis? Clique em afiliados.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Ao continuar, você concorda com os termos de uso."
        ),
        
        # Mensagem de acesso bloqueado
        "BLOCKED_MESSAGE": (
            "🚫 Acesso Bloqueado\n\n"
            "Você precisa se inscrever no nosso Canal/Grupo Obrigatório para usar o bot.\n\n"
            "📢 Canal: {channel_link}"
        ),
        
        # Mensagem do menu principal
        "MENU_MESSAGE": "📋 Menu Principal\nEscolha uma opção abaixo:",
        
        # Mensagem do catálogo
        "CATALOG_MESSAGE": "🛒✨ Selecione a categoria do seu Gift Card abaixo:",
        
        # Mensagem de saldo insuficiente
        "INSUFFICIENT_BALANCE": (
            "🚫 Saldo Insuficiente\n\n"
            "💰 Precisa: R$ {preco}\n"
            "💳 Você tem: R$ {saldo}\n\n"
            "Recarregue seu saldo para continuar."
        ),
        
        # Mensagem do PIX
        "PIX_MESSAGE": (
            "💠 Recarga via PIX\n\n"
            "Digite o valor que deseja adicionar.\n"
            "📌 Mínimo: R$ {min_value}\n"
            "📌 Máximo: R$ {max_value}\n"
            "⏳ Expiração: {expiration} minutos\n\n"
            "Digite apenas números.\n"
            "Ex: 50"
        ),
        
        # Mensagem de PIX gerado
        "PIX_GENERATED": (
            "🟢 PAGAMENTO VIA PIX GERADO\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 Valor: R$ {valor}\n"
            "🕒 Validade: {expiracao}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📲 Como pagar:\n"
            "1️⃣ Abra o app do seu banco\n"
            "2️⃣ Escolha pagar via PIX\n"
            "3️⃣ Escaneie o QR Code\n\n"
            "👇 Ou copie o código abaixo:"
        ),
        
        # Mensagem de PIX aprovado
        "PIX_APPROVED": (
            "✅ PIX PAGAMENTO CONFIRMADO!\n\n"
            "💰 Valor: R$ {valor}\n"
            "💳 Saldo adicionado: R$ {valor}\n\n"
            "Saldo anterior: R$ {saldo_anterior}\n"
            "+ R$ {valor}\n"
            "= R$ {saldo_atual}"
        ),
        
        # Mensagem de PIX expirado
        "PIX_EXPIRED": (
            "⌛ PIX EXPIRADO\n\n"
            "O pagamento não foi identificado dentro do prazo.\n"
            "💰 Valor: R$ {valor}\n"
            "Nenhum saldo foi adicionado."
        ),
        
        # Mensagem de compra realizada
        "PURCHASE_SUCCESS": (
            "✅ Compra realizada com sucesso!\n\n"
            "🎁 Produto: {produto}\n"
            "💰 Valor: R$ {preco}\n"
            "💳 Saldo restante: R$ {saldo}\n\n"
            "📦 Seu produto:\n"
            "{conteudo_entrega}"
        ),
        
        # Mensagem de perfil
        "PROFILE_MESSAGE": (
            "👤 Meu Perfil\n\n"
            "🆔 ID: {telegram_id}\n"
            "👤 Nome: {nome}\n"
            "💰 Saldo: R$ {saldo}\n"
            "🛒 Compras: {compras}\n"
            "💸 Total Gasto: R$ {total_gasto}"
        ),
        
        # Mensagem de histórico vazio
        "EMPTY_HISTORY": "📭 Você ainda não fez nenhuma compra.",
        
        # Mensagem de afiliados
        "AFFILIATE_MESSAGE": (
            "🤝 Programa de Afiliados\n\n"
            "📌 Seu link exclusivo:\n"
            "{link_afiliado}\n\n"
            "💰 Ganhe saldo grátis indicando seu link!\n"
            "• Comissão válida para depósitos\n"
            "• Troque por saldo no bot\n"
            "• Ganhos ilimitados 🚀\n\n"
            "📢 Compartilhe seu link e comece a lucrar!"
        ),
        
        # Mensagem de suporte
        "SUPPORT_MESSAGE": (
            "💬 Suporte\n\n"
            "Precisa de ajuda? Entre em contato:\n"
            "{support_link}\n\n"
            "Descreva sua dúvida que retornaremos em breve."
        ),
        
        # Mensagem de erro genérica
        "ERROR_MESSAGE": "❌ Ocorreu um erro. Tente novamente ou use /menu.",
    }
    
    # ===========================================
    # CONFIGURAÇÕES DE TEMPO
    # ===========================================
    # Janela para contador de "pessoas visualizando" (em segundos)
    VIEWER_WINDOW_SECONDS: int = int(os.getenv("VIEWER_WINDOW_SECONDS", "300"))  # 5 minutos
    
    # Tempo para limpeza de mensagens temporárias (em segundos)
    TEMP_MESSAGE_TTL: int = int(os.getenv("TEMP_MESSAGE_TTL", "1800"))  # 30 minutos
    
    # Intervalo de polling para verificar pagamentos (em segundos)
    PIX_POLL_INTERVAL: int = int(os.getenv("PIX_POLL_INTERVAL", "30"))
    
    # ===========================================
    # CONFIGURAÇÕES DE ARMAZENAMENTO
    # ===========================================
    BASE_DIR: Path = Path(__file__).parent
    MEDIA_DIR: Path = BASE_DIR / "storage" / "media"
    LOG_DIR: Path = BASE_DIR / "logs"
    
    # ===========================================
    # CONFIGURAÇÕES DE ADMIN
    # ===========================================
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # ===========================================
    # MÉTODOS UTILITÁRIOS
    # ===========================================
    
    @classmethod
    def get_message(cls, key: str, **kwargs) -> str:
        """Retorna uma mensagem formatada com as variáveis"""
        message = cls.MESSAGES.get(key, cls.MESSAGES["ERROR_MESSAGE"])
        return message.format(**kwargs)
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Verifica se um usuário é administrador"""
        return user_id in cls.ADMIN_IDS
    
    @classmethod
    def validate_pix_value(cls, value: float) -> tuple[bool, str]:
        """Valida se o valor do PIX está dentro dos limites"""
        if value < cls.PIX_MIN_VALUE:
            return False, f"Valor mínimo é R$ {cls.PIX_MIN_VALUE:.2f}"
        if value > cls.PIX_MAX_VALUE:
            return False, f"Valor máximo é R$ {cls.PIX_MAX_VALUE:.2f}"
        return True, ""
    
    @classmethod
    def get_payment_config(cls) -> Dict[str, Any]:
        """Retorna configuração completa de pagamento"""
        return {
            "provider": cls.PIX_PROVIDER,
            "api_url": cls.PIX_API_URL,
            "api_key": cls.PIX_API_KEY,
            "client_id": cls.PIX_CLIENT_ID,
            "client_secret": cls.PIX_CLIENT_SECRET,
            "webhook_url": cls.PIX_WEBHOOK_URL,
            "environment": cls.PIX_ENVIRONMENT,
            "min_value": cls.PIX_MIN_VALUE,
            "max_value": cls.PIX_MAX_VALUE,
            "expiration_minutes": cls.PIX_EXPIRATION_MINUTES,
        }
    
    @classmethod
    def update_from_db(cls, db_settings: Dict[str, Any]):
        """Atualiza configurações a partir do banco de dados"""
        # Este método será chamado quando as configurações do painel admin
        # forem carregadas do banco de dados
        for key, value in db_settings.items():
            if hasattr(cls, key.upper()):
                setattr(cls, key.upper(), value)


# Instância global para fácil importação
settings = Settings()
