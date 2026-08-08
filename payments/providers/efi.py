"""
Provedor Efí Bank (antiga Gerencianet)
Implementação para API PIX da Efí
"""

import logging
import httpx
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from payments.base import (
    BasePaymentProvider,
    AuthenticationError,
    PaymentCreationError,
)

logger = logging.getLogger(__name__)


class EfiProvider(BasePaymentProvider):
    """
    Provedor Efí Bank
    
    Documentação: https://dev.efipay.com.br/
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = None
        self.base_url = (
            "https://api-pix.gerencianet.com.br"
            if config.get("environment") == "production"
            else "https://api-pix-h.gerencianet.com.br"
        )
        self.http_client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtém cliente HTTP"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self.http_client
    
    async def authenticate(self) -> bool:
        """
        Autentica com Efí usando certificado ou client credentials
        """
        try:
            client_id = self.config.get("client_id")
            client_secret = self.config.get("client_secret")
            
            if not client_id or not client_secret:
                logger.error("Efi: client_id e client_secret necessários")
                return False
            
            # Basic Auth
            auth_string = f"{client_id}:{client_secret}"
            auth_b64 = base64.b64encode(auth_string.encode()).decode()
            
            client = await self._get_client()
            
            response = await client.post(
                "/oauth/token",
                json={"grant_type": "client_credentials"},
                headers={"Authorization": f"Basic {auth_b64}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.is_connected = True
                
                client.headers["Authorization"] = f"Bearer {self.access_token}"
                
                logger.info("Efi: autenticado com sucesso")
                return True
            else:
                logger.error(f"Efi: falha na autenticação - {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Efi: erro de autenticação - {e}")
            return False
    
    async def create_pix_charge(
        self,
        amount: float,
        description: str,
        expiration_minutes: int = 30,
        payer_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Cria cobrança PIX na Efí
        """
        if not self.is_connected:
            await self.authenticate()
            if not self.is_connected:
                return {"success": False, "error": "Não autenticado"}
        
        try:
            client = await self._get_client()
            
            # Gera txid único
            import uuid
            txid = uuid.uuid4().hex[:32]
            
            # Calcula expiração
            expiration = int((datetime.utcnow() + timedelta(minutes=expiration_minutes)).timestamp())
            
            cob_data = {
                "calendario": {
                    "expiracao": expiration,
                },
                "valor": {
                    "original": f"{amount:.2f}",
                },
                "chave": self.config.get("pix_key", ""),  # Chave PIX da conta
                "solicitacaoPagador": description[:140],
            }
            
            # Cria cobrança
            response = await client.put(
                f"/v2/cob/{txid}",
                json=cob_data,
            )
            
            if response.status_code in [200, 201]:
                cob = response.json()
                
                # Gera QR Code
                qr_response = await client.get(f"/v2/loc/{cob['loc']['id']}/qrcode")
                
                pix_code = None
                qr_code_base64 = None
                
                if qr_response.status_code == 200:
                    qr_data = qr_response.json()
                    pix_code = qr_data.get("qrcode")
                    qr_code_base64 = qr_data.get("imagemQrcode")
                
                logger.info(f"Efi: cobrança criada - txid={txid}")
                
                return {
                    "success": True,
                    "transaction_id": txid,
                    "pix_code": pix_code,
                    "qr_code_base64": qr_code_base64,
                    "qr_code_url": None,
                    "expires_at": datetime.fromtimestamp(expiration).isoformat(),
                }
            else:
                error_msg = f"Erro {response.status_code}: {response.text}"
                logger.error(f"Efi: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Efi: erro ao criar cobrança - {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica status da cobrança na Efí
        """
        if not self.is_connected:
            await self.authenticate()
        
        try:
            client = await self._get_client()
            
            response = await client.get(f"/v2/cob/{transaction_id}")
            
            if response.status_code == 200:
                cob = response.json()
                
                status_map = {
                    "ATIVA": "pending",
                    "CONCLUIDA": "approved",
                    "REMOVIDA_PELO_USUARIO_RECEBEDOR": "cancelled",
                    "REMOVIDA_PELO_PSP": "expired",
                }
                
                ef_status = cob.get("status", "ATIVA")
                our_status = status_map.get(ef_status, "pending")
                
                return {
                    "success": True,
                    "status": our_status,
                    "amount": float(cob.get("valor", {}).get("original", 0)),
                    "paid_at": datetime.now() if our_status == "approved" else None,
                }
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Efi: erro ao verificar status - {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Cancela cobrança na Efí
        """
        if not self.is_connected:
            await self.authenticate()
        
        try:
            client = await self._get_client()
            
            response = await client.patch(
                f"/v2/cob/{transaction_id}",
                json={"status": "REMOVIDA_PELO_USUARIO_RECEBEDOR"},
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Cobrança cancelada"}
            else:
                return {"success": False, "error": f"Erro {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa webhook da Efí
        """
        try:
            pix_data = payload.get("pix", [])
            
            if pix_data:
                txid = pix_data[0].get("txid")
                if txid:
                    status_result = await self.check_payment_status(txid)
                    return {
                        "success": True,
                        "transaction_id": txid,
                        "status": status_result.get("status"),
                    }
            
            return {"success": False, "error": "txid não encontrado"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa conexão com Efí
        """
        try:
            if not self.is_connected:
                auth_result = await self.authenticate()
                if not auth_result:
                    return {"success": False, "error": "Falha na autenticação"}
            
            return {"success": True, "message": "Efí conectado com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Fecha cliente HTTP"""
        if self.http_client:
            await self.http_client.aclose()
