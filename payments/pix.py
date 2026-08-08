"""
Serviço principal de pagamentos PIX
Orquestra a comunicação com os provedores e o banco de dados
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from config import settings
from database.connection import get_db
from database.models.payment import Payment, PixTransaction
from database.models.user import User
from database.repositories.payment_repository import PaymentRepository
from database.repositories.user_repository import UserRepository
from payments.base import (
    BasePaymentProvider,
    PaymentError,
    PaymentCreationError,
    PaymentStatusError,
)
from payments.providers import get_provider

logger = logging.getLogger(__name__)


class PixPaymentService:
    """
    Serviço de pagamentos PIX
    
    Gerencia:
    - Criação de cobranças PIX
    - Verificação de status
    - Cancelamento
    - Processamento de webhooks
    - Atualização de saldo
    """
    
    def __init__(self):
        self.payment_repo = PaymentRepository()
        self.user_repo = UserRepository()
        self._provider = None
    
    async def _get_provider(self) -> BasePaymentProvider:
        """Obtém instância do provedor configurado"""
        if not self._provider:
            pix_config = settings.get_payment_config()
            self._provider = await get_provider(pix_config)
            await self._provider.authenticate()
        return self._provider
    
    async def create_pix_payment(
        self,
        telegram_id: int,
        amount: float,
        description: str = "Recarga de saldo"
    ) -> Dict[str, Any]:
        """
        Cria um novo pagamento PIX
        
        Args:
            telegram_id: ID do usuário no Telegram
            amount: Valor da recarga
            description: Descrição do pagamento
            
        Returns:
            Dict com dados do pagamento criado
        """
        try:
            # Valida valor
            if amount < settings.PIX_MIN_VALUE:
                return {
                    "success": False,
                    "error": f"Valor mínimo: R$ {settings.PIX_MIN_VALUE:.2f}"
                }
            
            if amount > settings.PIX_MAX_VALUE:
                return {
                    "success": False,
                    "error": f"Valor máximo: R$ {settings.PIX_MAX_VALUE:.2f}"
                }
            
            # Verifica se usuário existe
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if not user:
                return {"success": False, "error": "Usuário não encontrado"}
            
            # Verifica se já existe PIX pendente
            pending = await self.payment_repo.get_pending_payment(telegram_id)
            if pending:
                return {
                    "success": False,
                    "error": "Você já tem um PIX pendente. Cancele ou aguarde expirar.",
                    "pending_payment": pending.to_dict() if pending else None,
                }
            
            # Cria registro de pagamento no banco
            expires_at = datetime.utcnow() + timedelta(minutes=settings.PIX_EXPIRATION_MINUTES)
            
            payment = await self.payment_repo.create_payment(
                user_id=user.id,
                amount=amount,
                provider=settings.PIX_PROVIDER,
                expires_at=expires_at,
            )
            
            # Obtém provedor e cria cobrança
            try:
                provider = await self._get_provider()
                
                payer_info = {
                    "name": user.first_name or "Cliente",
                    "email": f"{telegram_id}@telegram.com",
                }
                
                pix_result = await provider.create_pix_charge(
                    amount=amount,
                    description=f"{description} - ID: {telegram_id}",
                    expiration_minutes=settings.PIX_EXPIRATION_MINUTES,
                    payer_info=payer_info,
                )
                
                if not pix_result.get("success"):
                    # Marca pagamento como falho
                    await self.payment_repo.update_payment_status(
                        payment.id, "failed"
                    )
                    return {
                        "success": False,
                        "error": pix_result.get("error", "Erro ao gerar PIX"),
                    }
                
                # Salva dados da transação PIX
                await self.payment_repo.create_pix_transaction(
                    payment_id=payment.id,
                    pix_code=pix_result.get("pix_code"),
                    qr_code_base64=pix_result.get("qr_code_base64"),
                    transaction_id=pix_result.get("transaction_id"),
                )
                
                # Atualiza pagamento com ID externo
                await self.payment_repo.update_payment(
                    payment.id,
                    external_id=pix_result.get("transaction_id"),
                )
                
                logger.info(f"PIX criado: user={telegram_id}, amount={amount}, tx={pix_result.get('transaction_id')}")
                
                return {
                    "success": True,
                    "pix_data": {
                        "id": payment.id,
                        "pix_code": pix_result.get("pix_code"),
                        "qr_code_base64": pix_result.get("qr_code_base64"),
                        "qr_code_image": None,  # Será gerado depois
                        "transaction_id": pix_result.get("transaction_id"),
                        "expires_at": expires_at.strftime("%d/%m/%Y %H:%M"),
                    },
                }
                
            except PaymentError as e:
                await self.payment_repo.update_payment_status(
                    payment.id, "failed"
                )
                logger.error(f"Erro ao criar PIX: {e}")
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logger.error(f"Erro inesperado ao criar PIX: {e}")
            return {"success": False, "error": "Erro interno ao processar pagamento"}
    
    async def check_pix_status(self, pix_id: int) -> Dict[str, Any]:
        """
        Verifica o status de um PIX
        
        Args:
            pix_id: ID do pagamento no banco
            
        Returns:
            Dict com status atualizado
        """
        try:
            # Busca pagamento
            payment = await self.payment_repo.get_payment_by_id(pix_id)
            if not payment:
                return {"success": False, "error": "Pagamento não encontrado"}
            
            # Se já foi aprovado ou cancelado, retorna status atual
            if payment.status in ["approved", "cancelled", "expired"]:
                return {
                    "success": True,
                    "status": payment.status,
                    "value": payment.amount,
                    "old_balance": 0,
                    "new_balance": 0,
                }
            
            # Consulta provedor
            pix_transaction = await self.payment_repo.get_pix_transaction(pix_id)
            
            if pix_transaction and pix_transaction.transaction_id:
                provider = await self._get_provider()
                result = await provider.check_payment_status(
                    pix_transaction.transaction_id
                )
                
                if not result.get("success"):
                    return {
                        "success": True,
                        "status": "pending",
                        "value": payment.amount,
                    }
                
                external_status = result.get("status")
                
                if external_status == "approved":
                    # Confirma pagamento
                    return await self._approve_payment(payment)
                    
                elif external_status == "expired":
                    # Marca como expirado
                    await self.payment_repo.update_payment_status(
                        payment.id, "expired"
                    )
                    return {
                        "success": True,
                        "status": "expired",
                        "value": payment.amount,
                    }
                    
                elif external_status == "cancelled":
                    await self.payment_repo.update_payment_status(
                        payment.id, "cancelled"
                    )
                    return {
                        "success": True,
                        "status": "cancelled",
                        "value": payment.amount,
                    }
            
            # Verifica expiração local
            if payment.expires_at and datetime.utcnow() > payment.expires_at:
                await self.payment_repo.update_payment_status(
                    payment.id, "expired"
                )
                return {
                    "success": True,
                    "status": "expired",
                    "value": payment.amount,
                }
            
            return {
                "success": True,
                "status": "pending",
                "value": payment.amount,
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar PIX: {e}")
            return {"success": False, "error": str(e)}
    
    async def _approve_payment(self, payment: Payment) -> Dict[str, Any]:
        """
        Aprova um pagamento e adiciona saldo
        
        Args:
            payment: Objeto Payment
            
        Returns:
            Dict com resultado
        """
        try:
            # Evita processamento duplicado
            if payment.status == "approved":
                return {
                    "success": True,
                    "status": "approved",
                    "value": payment.amount,
                    "message": "Pagamento já foi aprovado",
                }
            
            # Atualiza status do pagamento
            await self.payment_repo.update_payment_status(
                payment.id, 
                "approved",
                approved_at=datetime.utcnow()
            )
            
            # Busca usuário
            user = await self.user_repo.get_by_id(payment.user_id)
            if not user:
                return {"success": False, "error": "Usuário não encontrado"}
            
            old_balance = user.balance
            
            # Adiciona saldo
            await self.user_repo.add_balance(
                user.telegram_id, 
                payment.amount
            )
            
            # Recarrega usuário
            user = await self.user_repo.get_by_id(payment.user_id)
            new_balance = user.balance if user else old_balance + payment.amount
            
            # Processa comissão de afiliado
            await self._process_affiliate_commission(payment)
            
            logger.info(
                f"PIX aprovado: user={user.telegram_id if user else 'N/A'}, "
                f"amount={payment.amount}, balance={old_balance}->{new_balance}"
            )
            
            return {
                "success": True,
                "status": "approved",
                "value": payment.amount,
                "old_balance": old_balance,
                "new_balance": new_balance,
            }
            
        except Exception as e:
            logger.error(f"Erro ao aprovar pagamento: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_affiliate_commission(self, payment: Payment):
        """
        Processa comissão de afiliado após pagamento aprovado
        
        Args:
            payment: Pagamento aprovado
        """
        try:
            from database.models.affiliate import Affiliate
            from database.repositories.affiliate_repository import AffiliateRepository
            
            # Busca usuário
            user = await self.user_repo.get_by_id(payment.user_id)
            if not user or not user.referrer_id:
                return
            
            # Verifica valor mínimo para comissão
            if payment.amount < settings.AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION:
                return
            
            affiliate_repo = AffiliateRepository()
            
            # Calcula comissão
            commission_rate = settings.AFFILIATE_COMMISSION_PERCENT / 100
            commission_amount = payment.amount * commission_rate
            
            # Cria comissão
            await affiliate_repo.create_commission(
                affiliate_id=user.referrer_id,
                referred_id=user.telegram_id,
                payment_id=payment.id,
                deposit_amount=payment.amount,
                commission_rate=settings.AFFILIATE_COMMISSION_PERCENT,
                commission_amount=commission_amount,
            )
            
            # Adiciona saldo ao afiliado
            await self.user_repo.add_balance(
                user.referrer_id, 
                commission_amount
            )
            
            # Atualiza ganhos do afiliado
            affiliate_user = await self.user_repo.get_by_telegram_id(user.referrer_id)
            if affiliate_user:
                await self.user_repo.update(
                    affiliate_user.id,
                    affiliate_earnings=affiliate_user.affiliate_earnings + commission_amount,
                )
            
            logger.info(
                f"Comissão processada: affiliate={user.referrer_id}, "
                f"referred={user.telegram_id}, commission={commission_amount}"
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar comissão: {e}")
    
    async def cancel_pix(self, pix_id: int) -> Dict[str, Any]:
        """
        Cancela um PIX pendente
        
        Args:
            pix_id: ID do pagamento
            
        Returns:
            Dict com resultado
        """
        try:
            payment = await self.payment_repo.get_payment_by_id(pix_id)
            
            if not payment:
                return {"success": False, "error": "Pagamento não encontrado"}
            
            if payment.status != "pending":
                return {
                    "success": False,
                    "error": f"Pagamento não pode ser cancelado (status: {payment.status})",
                }
            
            # Cancela no provedor
            pix_transaction = await self.payment_repo.get_pix_transaction(pix_id)
            
            if pix_transaction and pix_transaction.transaction_id:
                try:
                    provider = await self._get_provider()
                    await provider.cancel_payment(pix_transaction.transaction_id)
                except Exception as e:
                    logger.warning(f"Erro ao cancelar no provedor: {e}")
            
            # Atualiza status
            await self.payment_repo.update_payment_status(payment.id, "cancelled")
            
            logger.info(f"PIX cancelado: id={pix_id}")
            
            return {"success": True, "message": "PIX cancelado com sucesso"}
            
        except Exception as e:
            logger.error(f"Erro ao cancelar PIX: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_pending_pix(self, telegram_id: int) -> Optional[Dict]:
        """
        Busca PIX pendente do usuário
        
        Args:
            telegram_id: ID do usuário
            
        Returns:
            Dados do PIX pendente ou None
        """
        payment = await self.payment_repo.get_pending_payment(telegram_id)
        return payment.to_dict() if payment else None
    
    async def get_transactions(
        self, 
        status: str = "all", 
        page: int = 1, 
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Lista transações com filtros
        
        Args:
            status: Filtro de status
            page: Página
            per_page: Itens por página
            
        Returns:
            Dict com transações e metadados de paginação
        """
        return await self.payment_repo.get_transactions(status, page, per_page)
    
    async def get_transaction_detail(self, trans_id: int) -> Optional[Dict]:
        """
        Busca detalhes de uma transação
        
        Args:
            trans_id: ID da transação
            
        Returns:
            Dict com detalhes
        """
        payment = await self.payment_repo.get_payment_detail(trans_id)
        return payment.to_dict() if payment else None
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa notificação webhook do provedor
        
        Args:
            payload: Dados recebidos
            
        Returns:
            Resultado do processamento
        """
        try:
            provider = await self._get_provider()
            result = await provider.process_webhook(payload)
            
            if not result.get("success"):
                return result
            
            transaction_id = result.get("transaction_id")
            
            if transaction_id:
                # Busca pagamento pelo ID externo
                payment = await self.payment_repo.get_payment_by_external_id(
                    transaction_id
                )
                
                if payment:
                    status = result.get("status")
                    
                    if status == "approved":
                        await self._approve_payment(payment)
                    elif status == "expired":
                        await self.payment_repo.update_payment_status(
                            payment.id, "expired"
                        )
                    elif status == "cancelled":
                        await self.payment_repo.update_payment_status(
                            payment.id, "cancelled"
                        )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa conexão com o provedor PIX
        
        Returns:
            Resultado do teste
        """
        try:
            provider = await self._get_provider()
            return await provider.test_connection()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    async def check_expired_payments(self):
        """
        Verifica e atualiza pagamentos expirados
        Deve ser chamado periodicamente (job)
        """
        try:
            expired = await self.payment_repo.get_expired_pending_payments()
            
            for payment in expired:
                await self.payment_repo.update_payment_status(
                    payment.id, "expired"
                )
                logger.info(f"PIX expirado automaticamente: id={payment.id}")
            
            if expired:
                logger.info(f"{len(expired)} PIX expirados processados")
                
        except Exception as e:
            logger.error(f"Erro ao verificar PIX expirados: {e}")
