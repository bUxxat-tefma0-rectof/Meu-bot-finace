"""
Classe base abstrata para provedores de pagamento
Define a interface que todos os provedores devem implementar
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BasePaymentProvider(ABC):
    """
    Classe base para todos os provedores de pagamento PIX
    
    Cada provedor (Mercado Pago, Efi, Zendry, etc) deve herdar
    desta classe e implementar todos os métodos abstratos.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o provedor com configurações
        
        Args:
            config: Dicionário com configurações do provedor
                - api_url: URL base da API
                - api_key: Chave de API
                - client_id: ID do cliente
                - client_secret: Secret do cliente
                - webhook_url: URL do webhook
                - environment: 'sandbox' ou 'production'
        """
        self.config = config
        self.provider_name = self.__class__.__name__
        self.is_connected = False
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Autentica com a API do provedor
        Retorna True se autenticado com sucesso
        """
        pass
    
    @abstractmethod
    async def create_pix_charge(
        self, 
        amount: float, 
        description: str,
        expiration_minutes: int = 30,
        payer_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Cria uma cobrança PIX
        
        Args:
            amount: Valor da cobrança
            description: Descrição da cobrança
            expiration_minutes: Tempo de expiração em minutos
            payer_info: Informações do pagador (opcional)
            
        Returns:
            Dict com:
                - success: bool
                - transaction_id: ID da transação no provedor
                - pix_code: Código PIX copia e cola
                - qr_code_base64: QR Code em base64
                - qr_code_url: URL do QR Code
                - expires_at: Data/hora de expiração
                - error: Mensagem de erro (se falha)
        """
        pass
    
    @abstractmethod
    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica o status de um pagamento
        
        Args:
            transaction_id: ID da transação no provedor
            
        Returns:
            Dict com:
                - success: bool
                - status: 'pending', 'approved', 'expired', 'cancelled', 'error'
                - amount: Valor pago
                - paid_at: Data/hora do pagamento
                - error: Mensagem de erro (se falha)
        """
        pass
    
    @abstractmethod
    async def cancel_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Cancela um pagamento pendente
        
        Args:
            transaction_id: ID da transação
            
        Returns:
            Dict com:
                - success: bool
                - error: Mensagem de erro (se falha)
        """
        pass
    
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa notificação webhook do provedor
        
        Args:
            payload: Dados recebidos do webhook
            
        Returns:
            Dict com:
                - success: bool
                - transaction_id: ID da transação
                - status: Novo status
                - error: Mensagem de erro (se falha)
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão com a API do provedor
        
        Returns:
            Dict com:
                - success: bool
                - message: Mensagem de status
                - error: Mensagem de erro (se falha)
        """
        pass
    
    def _validate_config(self) -> bool:
        """Valida se as configurações necessárias estão presentes"""
        required_fields = ['api_url', 'api_key']
        
        for field in required_fields:
            if not self.config.get(field):
                logger.error(f"Configuração ausente: {field}")
                return False
        
        return True
    
    def _format_amount(self, amount: float) -> str:
        """Formata valor para o formato esperado pela API"""
        return f"{amount:.2f}"
    
    def _calculate_expiration(self, minutes: int) -> str:
        """Calcula data de expiração formatada"""
        from datetime import timedelta
        expiration = datetime.utcnow() + timedelta(minutes=minutes)
        return expiration.isoformat()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Retorna informações do provedor"""
        return {
            "name": self.provider_name,
            "is_connected": self.is_connected,
            "environment": self.config.get("environment", "sandbox"),
            "api_url": self.config.get("api_url", "")[:50] + "...",
        }


class PaymentError(Exception):
    """Exceção base para erros de pagamento"""
    pass


class AuthenticationError(PaymentError):
    """Erro de autenticação"""
    pass


class PaymentCreationError(PaymentError):
    """Erro ao criar pagamento"""
    pass


class PaymentStatusError(PaymentError):
    """Erro ao verificar status"""
    pass


class PaymentCancellationError(PaymentError):
    """Erro ao cancelar pagamento"""
    pass


class WebhookProcessingError(PaymentError):
    """Erro ao processar webhook"""
    pass
