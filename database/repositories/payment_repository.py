"""
Repositório de Pagamentos
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import joinedload

from database.models.payment import Payment, PixTransaction
from database.models.user import User
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class PaymentRepository(BaseRepository[Payment]):
    """Repositório para operações com pagamentos"""
    
    def __init__(self):
        super().__init__(Payment)
    
    async def create_payment(
        self,
        user_id: int,
        amount: float,
        provider: str = "pix",
        expires_at: datetime = None,
    ) -> Payment:
        """Cria um novo registro de pagamento"""
        db = await get_db()
        try:
            payment = Payment(
                user_id=user_id,
                amount=amount,
                provider=provider,
                status="pending",
                expires_at=expires_at,
            )
            db.add(payment)
            await db.commit()
            await db.refresh(payment)
            
            logger.info(f"Pagamento criado: id={payment.id}, user={user_id}, amount={amount}")
            
            return payment
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar pagamento: {e}")
            raise
        finally:
            await db.close()
    
    async def create_pix_transaction(
        self,
        payment_id: int,
        pix_code: str = None,
        qr_code_base64: str = None,
        transaction_id: str = None,
    ) -> PixTransaction:
        """Cria registro de transação PIX"""
        db = await get_db()
        try:
            pix = PixTransaction(
                payment_id=payment_id,
                pix_code=pix_code,
                qr_code_base64=qr_code_base64,
                transaction_id=transaction_id,
            )
            db.add(pix)
            await db.commit()
            await db.refresh(pix)
            
            return pix
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar transação PIX: {e}")
            raise
        finally:
            await db.close()
    
    async def get_pending_payment(self, telegram_id: int) -> Optional[Payment]:
        """Busca pagamento pendente do usuário"""
        db = await get_db()
        try:
            # Busca usuário
            user_result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Busca pagamento pendente
            result = await db.execute(
                select(Payment)
                .where(
                    and_(
                        Payment.user_id == user.id,
                        Payment.status == "pending",
                    )
                )
                .order_by(Payment.id.desc())
            )
            payment = result.scalars().first()
            
            return payment
        finally:
            await db.close()
    
    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Busca pagamento por ID"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Payment)
                .options(joinedload(Payment.user))
                .where(Payment.id == payment_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_payment_by_external_id(self, external_id: str) -> Optional[Payment]:
        """Busca pagamento pelo ID externo"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Payment).where(Payment.external_id == external_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_pix_transaction(self, payment_id: int) -> Optional[PixTransaction]:
        """Busca transação PIX do pagamento"""
        db = await get_db()
        try:
            result = await db.execute(
                select(PixTransaction)
                .where(PixTransaction.payment_id == payment_id)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def update_payment_status(
        self,
        payment_id: int,
        status: str,
        **kwargs,
    ) -> bool:
        """Atualiza status do pagamento"""
        db = await get_db()
        try:
            update_data = {"status": status, **kwargs}
            
            await db.execute(
                update(Payment)
                .where(Payment.id == payment_id)
                .values(**update_data)
            )
            await db.commit()
            
            logger.info(f"Pagamento {payment_id} atualizado: status={status}")
            
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar pagamento: {e}")
            return False
        finally:
            await db.close()
    
    async def get_payment_detail(self, payment_id: int) -> Optional[Payment]:
        """Busca detalhes completos do pagamento"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Payment)
                .options(
                    joinedload(Payment.user),
                    joinedload(Payment.pix_transaction),
                )
                .where(Payment.id == payment_id)
            )
            return result.unique().scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_transactions(
        self,
        status: str = "all",
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """Lista transações com filtros"""
        db = await get_db()
        try:
            offset = (page - 1) * per_page
            
            # Query base
            query = select(Payment).options(joinedload(Payment.user))
            
            # Filtro de status
            if status != "all":
                query = query.where(Payment.status == status)
            
            # Conta total
            count_query = select(func.count(Payment.id))
            if status != "all":
                count_query = count_query.where(Payment.status == status)
            
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Busca paginada
            result = await db.execute(
                query
                .order_by(Payment.id.desc())
                .limit(per_page)
                .offset(offset)
            )
            transactions = result.unique().scalars().all()
            
            return {
                "transactions": transactions,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "page": page,
            }
        finally:
            await db.close()
    
    async def get_expired_pending_payments(self) -> List[Payment]:
        """Busca pagamentos pendentes expirados"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Payment)
                .where(
                    and_(
                        Payment.status == "pending",
                        Payment.expires_at < datetime.utcnow(),
                    )
                )
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_pix_count_today(self) -> int:
        """PIX gerados hoje"""
        db = await get_db()
        try:
            today = datetime.utcnow().date()
            result = await db.execute(
                select(func.count(Payment.id))
                .where(
                    and_(
                        func.date(Payment.created_at) == today,
                        Payment.provider == "pix",
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_pending_pix_count(self) -> int:
        """PIX pendentes"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.count(Payment.id))
                .where(
                    and_(
                        Payment.status == "pending",
                        Payment.provider == "pix",
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_approved_pix_count_today(self) -> int:
        """PIX aprovados hoje"""
        db = await get_db()
        try:
            today = datetime.utcnow().date()
            result = await db.execute(
                select(func.count(Payment.id))
                .where(
                    and_(
                        Payment.status == "approved",
                        Payment.provider == "pix",
                        func.date(Payment.approved_at) == today,
                    )
                )
            )
            return result.scalar() or 0
        finally:
            await db.close()
