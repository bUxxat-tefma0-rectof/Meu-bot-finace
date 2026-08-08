"""
Serviço de Carteira/Saldo
Gerencia recargas, PIX e transações
"""

import logging
from typing import Dict, Any, Optional

from payments.pix import PixPaymentService

logger = logging.getLogger(__name__)


class WalletService:
    """
    Serviço de carteira
    
    Fachada para o serviço de pagamentos PIX
    """
    
    def __init__(self):
        self.pix_service = PixPaymentService()
    
    async def create_pix_payment(
        self,
        telegram_id: int,
        amount: float,
    ) -> Dict[str, Any]:
        """
        Cria um pagamento PIX para recarga
        
        Args:
            telegram_id: ID do usuário
            amount: Valor
            
        Returns:
            Dados do PIX gerado
        """
        return await self.pix_service.create_pix_payment(
            telegram_id=telegram_id,
            amount=amount,
            description="Recarga de saldo",
        )
    
    async def check_pix_status(self, pix_id: int) -> Dict[str, Any]:
        """
        Verifica status do PIX
        
        Args:
            pix_id: ID do pagamento
            
        Returns:
            Status atualizado
        """
        return await self.pix_service.check_pix_status(pix_id)
    
    async def cancel_pix(self, pix_id: int) -> Dict[str, Any]:
        """
        Cancela PIX pendente
        
        Args:
            pix_id: ID do pagamento
            
        Returns:
            Resultado
        """
        return await self.pix_service.cancel_pix(pix_id)
    
    async def get_pending_pix(self, telegram_id: int) -> Optional[Dict]:
        """
        Busca PIX pendente do usuário
        
        Args:
            telegram_id: ID do usuário
            
        Returns:
            PIX pendente ou None
        """
        return await self.pix_service.get_pending_pix(telegram_id)
    
    async def get_transactions(
        self,
        status: str = "all",
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """
        Lista transações (admin)
        
        Args:
            status: Filtro
            page: Página
            per_page: Itens por página
            
        Returns:
            Transações paginadas
        """
        return await self.pix_service.get_transactions(status, page, per_page)
    
    async def get_transaction_detail(self, trans_id: int) -> Optional[Dict]:
        """
        Detalhes de transação
        
        Args:
            trans_id: ID da transação
            
        Returns:
            Detalhes
        """
        return await self.pix_service.get_transaction_detail(trans_id)
    
    async def check_expired_pix(self, context=None):
        """
        Verifica PIX expirados (job)
        """
        await self.pix_service.check_expired_payments()
    
    async def get_pix_count_today(self) -> int:
        """PIX gerados hoje"""
        from database.repositories.payment_repository import PaymentRepository
        repo = PaymentRepository()
        return await repo.get_pix_count_today()
    
    async def get_pending_pix_count(self) -> int:
        """PIX pendentes"""
        from database.repositories.payment_repository import PaymentRepository
        repo = PaymentRepository()
        return await repo.get_pending_pix_count()
    
    async def get_approved_pix_count_today(self) -> int:
        """PIX aprovados hoje"""
        from database.repositories.payment_repository import PaymentRepository
        repo = PaymentRepository()
        return await repo.get_approved_pix_count_today()
