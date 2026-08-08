"""
Provedor Mock para desenvolvimento e testes
Simula respostas de uma API PIX real
"""

import logging
import uuid
import random
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from payments.base import BasePaymentProvider

logger = logging.getLogger(__name__)


class MockProvider(BasePaymentProvider):
    """
    Provedor simulado para testes
    
    Gera QR Codes falsos e simula aprovações automáticas
    para desenvolvimento sem uma conta real de pagamento.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._payments = {}  # Armazena pagamentos simulados
        self.is_connected = True
        logger.info("MockProvider inicializado (ambiente de testes)")
    
    async def authenticate(self) -> bool:
        """Simula autenticação"""
        logger.info("MockProvider: autenticação simulada")
        self.is_connected = True
        return True
    
    async def create_pix_charge(
        self,
        amount: float,
        description: str,
        expiration_minutes: int = 30,
        payer_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Cria uma cobrança PIX simulada
        """
        try:
            # Gera ID único
            transaction_id = f"mock_{uuid.uuid4().hex[:16]}"
            
            # Gera código PIX falso
            pix_code = self._generate_fake_pix_code(amount)
            
            # Gera QR Code falso (placeholder)
            qr_code_base64 = self._generate_fake_qr_code(transaction_id)
            
            # Calcula expiração
            expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            # Armazena pagamento
            self._payments[transaction_id] = {
                "amount": amount,
                "description": description,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "payer_info": payer_info,
            }
            
            logger.info(f"MockProvider: PIX criado - tx={transaction_id}, amount={amount}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "pix_code": pix_code,
                "qr_code_base64": qr_code_base64,
                "qr_code_url": f"https://mock-qr.example.com/{transaction_id}",
                "expires_at": expires_at.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"MockProvider: erro ao criar PIX - {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica status de pagamento simulado
        
        Simula aprovação automática após alguns segundos
        para facilitar testes.
        """
        payment = self._payments.get(transaction_id)
        
        if not payment:
            return {
                "success": False,
                "error": "Transação não encontrada",
            }
        
        # Simula aprovação automática após 10 segundos (para testes)
        elapsed = (datetime.utcnow() - payment["created_at"]).total_seconds()
        
        if elapsed > 10 and payment["status"] == "pending":
            # 80% de chance de aprovar automaticamente
            if random.random() < 0.8:
                payment["status"] = "approved"
                payment["paid_at"] = datetime.utcnow()
                logger.info(f"MockProvider: pagamento aprovado automaticamente - tx={transaction_id}")
        
        # Verifica expiração
        if payment["status"] == "pending" and datetime.utcnow() > payment["expires_at"]:
            payment["status"] = "expired"
        
        return {
            "success": True,
            "status": payment["status"],
            "amount": payment["amount"],
            "paid_at": payment.get("paid_at"),
        }
    
    async def cancel_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Cancela pagamento simulado"""
        payment = self._payments.get(transaction_id)
        
        if not payment:
            return {"success": False, "error": "Transação não encontrada"}
        
        if payment["status"] != "pending":
            return {"success": False, "error": "Pagamento não pode ser cancelado"}
        
        payment["status"] = "cancelled"
        logger.info(f"MockProvider: pagamento cancelado - tx={transaction_id}")
        
        return {"success": True, "message": "Pagamento cancelado"}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Processa webhook simulado"""
        transaction_id = payload.get("transaction_id") or payload.get("id")
        
        if not transaction_id:
            return {"success": False, "error": "ID não encontrado no payload"}
        
        payment = self._payments.get(transaction_id)
        
        if not payment:
            return {"success": False, "error": "Transação não encontrada"}
        
        # Atualiza status
        new_status = payload.get("status", "approved")
        payment["status"] = new_status
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": new_status,
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexão simulada"""
        return {
            "success": True,
            "message": "MockProvider conectado (simulação)",
        }
    
    def _generate_fake_pix_code(self, amount: float) -> str:
        """Gera um código PIX falso para testes"""
        hash_part = hashlib.md5(f"{amount}{uuid.uuid4()}".encode()).hexdigest()[:16]
        return (
            "00020126580014br.gov.bcb.pix0136"
            f"{hash_part}"
            "520400005303986540"
            f"{amount:.2f}".replace(".", "")
            "5802BR5925MockStore6009SAOPAULO62070503***6304"
            f"{random.randint(1000, 9999)}"
        )
    
    def _generate_fake_qr_code(self, transaction_id: str) -> str:
        """
        Gera um QR Code falso em base64
        Na prática, seria gerado com biblioteca qrcode + PIL
        """
        # Placeholder - um PNG mínimo em base64
        return (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "+P+/HgAFhAJ/ql+QhQAAAABJRU5ErkJggg=="
        )
