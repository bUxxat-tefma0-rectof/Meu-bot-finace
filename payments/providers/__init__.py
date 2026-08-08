"""
Provedores de pagamento PIX
Cada arquivo implementa um provedor específico
"""

import logging
from typing import Dict, Any

from payments.base import BasePaymentProvider

logger = logging.getLogger(__name__)

# Registro de provedores disponíveis
AVAILABLE_PROVIDERS = {
    "mercado_pago": "MercadoPagoProvider",
    "efi": "EfiProvider",
    "zendry": "ZendryProvider",
    "mock": "MockProvider",  # Para testes
}


async def get_provider(config: Dict[str, Any]) -> BasePaymentProvider:
    """
    Factory para obter instância do provedor configurado
    
    Args:
        config: Configurações do provedor (do settings ou banco)
        
    Returns:
        Instância do provedor
    """
    provider_name = config.get("provider", "mock")
    
    if provider_name == "mercado_pago":
        from payments.providers.mercado_pago import MercadoPagoProvider
        return MercadoPagoProvider(config)
    
    elif provider_name == "efi":
        from payments.providers.efi import EfiProvider
        return EfiProvider(config)
    
    elif provider_name == "zendry":
        from payments.providers.zendry import ZendryProvider
        return ZendryProvider(config)
    
    elif provider_name == "mock":
        from payments.providers.mock_provider import MockProvider
        return MockProvider(config)
    
    else:
        logger.warning(f"Provedor '{provider_name}' não encontrado, usando Mock")
        from payments.providers.mock_provider import MockProvider
        return MockProvider(config)
