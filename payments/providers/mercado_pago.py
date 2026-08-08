"""
Provedor Mercado Pago
Implementação real para API do Mercado Pago
"""

import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from payments.base import (
    BasePaymentProvider,
    AuthenticationError,
    PaymentCreationError,
    PaymentStatusError,
    PaymentCancellationError,
)

logger = logging.getLogger(__name__)


class MercadoPagoProvider(BasePaymentProvider):
    """
    Provedor Mercado Pago
    
    Documentação: https://www.mercadopago.com.br/developers/pt/reference
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = None
        self.base_url = "https://api.mercadopago.com/v1"
        self.http_client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtém cliente HTTP"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self.http_client
    
    async def authenticate(self) -> bool:
        """
        Autentica com Mercado Pago
        
        Usa Client ID e Client Secret para obter access token
        """
        try:
            client = await self._get_client()
            
            # Tenta autenticar com client_credentials
            response = await client.post(
                "/oauth/token",
                json={
                    "client_id": self.config.get("client_id"),
                    "client_secret": self.config.get("client_secret"),
                    "grant_type": "client_credentials",
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.is_connected = True
                
                # Atualiza headers com token
                client.headers["Authorization"] = f"Bearer {self.access_token}"
                
                logger.info("MercadoPago: autenticado com sucesso")
                return True
            else:
                # Tenta usar API Key diretamente
                api_key = self.config.get("api_key")
                if api_key:
                    self.access_token = api_key
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                    self.is_connected = True
                    logger.info("MercadoPago: usando API Key direta")
                    return True
                
                logger.error(f"MercadoPago: falha na autenticação - {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"MercadoPago: erro de autenticação - {e}")
            self.is_connected = False
            return False
    
    async def create_pix_charge(
        self,
        amount: float,
        description: str,
        expiration_minutes: int = 30,
        payer_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Cria cobrança PIX no Mercado Pago
        """
        if not self.is_connected:
            await self.authenticate()
            if not self.is_connected:
                return {"success": False, "error": "Não autenticado"}
        
        try:
            client = await self._get_client()
            
            # Prepara dados da cobrança
            expiration = (datetime.utcnow() + timedelta(minutes=expiration_minutes))
            
            payment_data = {
                "transaction_amount": float(amount),
                "description": description[:100],
                "payment_method_id": "pix",
                "payer": {
                    "email": payer_info.get("email", "cliente@email.com") if payer_info else "cliente@email.com",
                    "first_name": payer_info.get("name", "Cliente") if payer_info else "Cliente",
                },
                "date_of_expiration": expiration.strftime("%Y-%m-%dT%H:%M:%S.000-03:00"),
                "notification_url": self.config.get("webhook_url", ""),
            }
            
            # Cria pagamento
            response = await client.post("/payments", json=payment_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                transaction_id = str(data.get("id"))
                
                # Busca código PIX
                pix_code = None
                qr_code_base64 = None
                
                point_of_interaction = data.get("point_of_interaction", {})
                transaction_data = point_of_interaction.get("transaction_data", {})
                
                pix_code = transaction_data.get("qr_code")
                qr_code_base64 = transaction_data.get("qr_code_base64")
                
                logger.info(f"MercadoPago: pagamento criado - id={transaction_id}")
                
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "pix_code": pix_code,
                    "qr_code_base64": qr_code_base64,
                    "qr_code_url": None,
                    "expires_at": expiration.isoformat(),
                }
            else:
                error_msg = f"Erro {response.status_code}: {response.text}"
                logger.error(f"MercadoPago: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"MercadoPago: erro ao criar PIX - {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica status do pagamento no Mercado Pago
        """
        if not self.is_connected:
            await self.authenticate()
        
        try:
            client = await self._get_client()
            
            response = await client.get(f"/payments/{transaction_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                status_map = {
                    "pending": "pending",
                    "approved": "approved",
                    "authorized": "pending",
                    "in_process": "pending",
                    "in_mediation": "pending",
                    "rejected": "cancelled",
                    "cancelled": "cancelled",
                    "refunded": "cancelled",
                    "charged_back": "cancelled",
                }
                
                mp_status = data.get("status", "pending")
                our_status = status_map.get(mp_status, "pending")
                
                paid_at = None
                if data.get("date_approved"):
                    paid_at = datetime.fromisoformat(
                        data["date_approved"].replace("Z", "+00:00")
                    )
                
                return {
                    "success": True,
                    "status": our_status,
                    "amount": data.get("transaction_amount"),
                    "paid_at": paid_at,
                }
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            logger.error(f"MercadoPago: erro ao verificar status - {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Cancela pagamento no Mercado Pago
        """
        if not self.is_connected:
            await self.authenticate()
        
        try:
            client = await self._get_client()
            
            response = await client.put(
                f"/payments/{transaction_id}",
                json={"status": "cancelled"},
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "message": "Pagamento cancelado"}
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            logger.error(f"MercadoPago: erro ao cancelar - {e}")
            return {"success": False, "error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa webhook do Mercado Pago
        """
        try:
            # Webhook do MP pode vir de diferentes formas
            action = payload.get("action")
            data = payload.get("data", {})
            payment_id = data.get("id") or payload.get("id")
            
            if not payment_id:
                return {"success": False, "error": "ID não encontrado"}
            
            # Consulta status atual
            status_result = await self.check_payment_status(str(payment_id))
            
            return {
                "success": True,
                "transaction_id": str(payment_id),
                "status": status_result.get("status", "unknown"),
            }
            
        except Exception as e:
            logger.error(f"MercadoPago: erro no webhook - {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa conexão com Mercado Pago
        """
        try:
            if not self.is_connected:
                auth_result = await self.authenticate()
                if not auth_result:
                    return {
                        "success": False,
                        "error": "Falha na autenticação",
                    }
            
            client = await self._get_client()
            response = await client.get("/users/me")
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": f"Conectado como: {user_data.get('nickname', 'N/A')}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro {response.status_code}: {response.text}",
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Fecha cliente HTTP"""
        if self.http_client:
            await self.http_client.aclose()
