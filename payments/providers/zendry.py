"""
Provedor Zendry
Implementação para API PIX da Zendry
"""

import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from payments.base import BasePaymentProvider

logger = logging.getLogger(__name__)


class ZendryProvider(BasePaymentProvider):
    """
    Provedor Zendry
    
    Documentação: https://docs.zendry.com/
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("api_url", "https://api.zendry.com/v1")
        self.http_client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtém cliente HTTP"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
        return self.http_client
    
    async def authenticate(self) -> bool:
        """
        Autentica com Zendry (API Key)
        """
        try:
            if not self.api_key:
                logger.error("Zendry: API Key não configurada")
                return False
            
            # Testa a chave fazendo uma requisição simples
            client = await self._get_client()
            response = await client.get("/account/balance")
            
            if response.status_code == 200:
                self.is_connected = True
                logger.info("Zendry: autenticado com sucesso")
                return True
            else:
                logger.error(f"Zendry: falha na autenticação - {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Zendry: erro de autenticação - {e}")
            return False
    
    async def create_pix_charge(
        self,
        amount: float,
        description: str,
        expiration_minutes: int = 30,
        payer_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Cria cobrança PIX na Zendry
        """
        if not self.is_connected:
            await self.authenticate()
            if not self.is_connected:
                return {"success": False, "error": "Não autenticado"}
        
        try:
            client = await self._get_client()
            
            payload = {
                "amount": float(amount),
                "description": description[:200],
                "expiration_minutes": expiration_minutes,
            }
            
            response = await client.post("/pix/qrcode", json=payload)
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                return {
                    "success": True,
                    "transaction_id": data.get("id") or data.get("transaction_id"),
                    "pix_code": data.get("pix_code") or data.get("br_code"),
                    "qr_code_base64": data.get("qr_code_base64"),
                    "qr_code_url": data.get("qr_code_url"),
                    "expires_at": (datetime.utcnow() + timedelta(minutes=expiration_minutes)).isoformat(),
                }
            else:
                return {"success": False, "error": f"Erro {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"Zendry: erro ao criar PIX - {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica status na Zendry
        """
        try:
            client = await self._get_client()
            
            response = await client.get(f"/pix/status/{transaction_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                status_map = {
                    "pending": "pending",
                    "paid": "approved",
                    "expired": "expired",
                    "cancelled": "cancelled",
                    "failed": "cancelled",
                }
                
                return {
                    "success": True,
                    "status": status_map.get(data.get("status"), "pending"),
                    "amount": data.get("amount"),
                    "paid_at": datetime.now() if data.get("status") == "paid" else None,
                }
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cancel_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Cancela pagamento na Zendry
        """
        try:
            client = await self._get_client()
            
            response = await client.post(f"/pix/cancel/{transaction_id}")
            
            if response.status_code == 200:
                return {"success": True, "message": "Pagamento cancelado"}
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa webhook da Zendry
        """
        try:
            transaction_id = payload.get("transaction_id") or payload.get("id")
            status = payload.get("status", "approved")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": status,
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa conexão com Zendry
        """
        try:
            if not self.is_connected:
                auth_result = await self.authenticate()
                if not auth_result:
                    return {"success": False, "error": "Falha na autenticação"}
            
            return {"success": True, "message": "Zendry conectado com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Fecha cliente HTTP"""
        if self.http_client:
            await self.http_client.aclose()
