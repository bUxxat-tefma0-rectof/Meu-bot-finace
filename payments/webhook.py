"""
Servidor Webhook para receber notificações de pagamento
"""

import logging
import json
import hmac
import hashlib
from typing import Dict, Any, Optional

from config import settings
from payments.pix import PixPaymentService

logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Manipulador de webhooks de pagamento
    
    Recebe notificações dos provedores e processa
    a confirmação de pagamentos.
    """
    
    def __init__(self):
        self.pix_service = PixPaymentService()
    
    async def handle_webhook(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Processa um webhook recebido
        
        Args:
            provider: Nome do provedor (mercado_pago, efi, zendry)
            payload: Dados recebidos
            signature: Assinatura para validação (opcional)
            headers: Headers HTTP (opcional)
            
        Returns:
            Resultado do processamento
        """
        try:
            logger.info(f"Webhook recebido: provider={provider}")
            
            # Valida assinatura se disponível
            if signature and not self._validate_signature(provider, payload, signature):
                logger.warning("Webhook: assinatura inválida")
                return {"success": False, "error": "Assinatura inválida"}
            
            # Processa com o serviço PIX
            result = await self.pix_service.process_webhook(payload)
            
            if result.get("success"):
                logger.info(
                    f"Webhook processado: tx={result.get('transaction_id')}, "
                    f"status={result.get('status')}"
                )
            else:
                logger.error(f"Webhook falhou: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_signature(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """
        Valida assinatura do webhook
        
        Args:
            provider: Provedor
            payload: Dados
            signature: Assinatura recebida
            
        Returns:
            True se válido
        """
        try:
            if provider == "mercado_pago":
                return self._validate_mp_signature(payload, signature)
            elif provider == "efi":
                return self._validate_efi_signature(payload, signature)
            else:
                # Para desenvolvimento, aceita sem validação
                return True
        except Exception as e:
            logger.error(f"Erro ao validar assinatura: {e}")
            return False
    
    def _validate_mp_signature(self, payload: Dict, signature: str) -> bool:
        """Valida assinatura do Mercado Pago"""
        secret = settings.PIX_CLIENT_SECRET
        
        if not secret:
            return True  # Sem secret configurado, aceita
        
        # Converte payload para string
        payload_str = json.dumps(payload, separators=(",", ":"))
        
        # Calcula HMAC
        expected = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def _validate_efi_signature(self, payload: Dict, signature: str) -> bool:
        """Valida assinatura da Efí"""
        # Implementar conforme documentação da Efí
        return True
    
    async def get_webhook_url(self) -> str:
        """Retorna URL do webhook configurada"""
        return settings.PIX_WEBHOOK_URL


# Instância global
webhook_handler = WebhookHandler()


async def process_webhook_request(
    provider: str,
    body: bytes,
    headers: Dict[str, str],
) -> Dict[str, Any]:
    """
    Função auxiliar para processar requisição webhook
    
    Args:
        provider: Provedor
        body: Corpo da requisição em bytes
        headers: Headers HTTP
        
    Returns:
        Resultado
    """
    try:
        # Decodifica payload
        payload = json.loads(body.decode("utf-8"))
        
        # Extrai assinatura (varia por provedor)
        signature = (
            headers.get("X-Signature")
            or headers.get("X-Hub-Signature")
            or headers.get("Signature")
        )
        
        return await webhook_handler.handle_webhook(
            provider=provider,
            payload=payload,
            signature=signature,
            headers=headers,
        )
        
    except json.JSONDecodeError:
        return {"success": False, "error": "Payload inválido (JSON)"}
    except Exception as e:
        return {"success": False, "error": str(e)}
