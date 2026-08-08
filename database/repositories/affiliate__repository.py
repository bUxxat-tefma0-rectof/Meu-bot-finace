"""
Repositório de Afiliados
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, and_

from database.models.affiliate import Affiliate, AffiliateCommission
from database.models.payment import Payment
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class AffiliateRepository(BaseRepository[Affiliate]):
    """Repositório para operações com afiliados"""
    
    def __init__(self):
        super().__init__(Affiliate)
    
    async def create_affiliate(
        self,
        referrer_id: int,
        referred_id: int,
    ) -> Affiliate:
        """Cria relação de afiliado"""
        db = await get_db()
        try:
            # Verifica se já existe
            existing = await db.execute(
                select(Affiliate).where(Affiliate.referred_id == referred_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError("Usuário já foi indicado por alguém")
            
            affiliate = Affiliate(
                referrer_id=referrer_id,
                referred_id=referred_id,
            )
            db.add(affiliate)
            await db.commit()
            await db.refresh(affiliate)
            
            return affiliate
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def get_referral_count(self, referrer_id: int) -> int:
        """Conta indicados de um afiliado"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.count(Affiliate.id))
                .where(Affiliate.referrer_id == referrer_id)
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_referrals(self, referrer_id: int) -> List[Affiliate]:
        """Lista indicados"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Affiliate)
                .where(Affiliate.referrer_id == referrer_id)
                .order_by(Affiliate.id.desc())
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_total_commissions(self, affiliate_id: int) -> float:
        """Total de comissões de um afiliado"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(AffiliateCommission.commission_amount))
                .where(
                    and_(
                        AffiliateCommission.affiliate_id == affiliate_id,
                        AffiliateCommission.status == "credited",
                    )
                )
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
    
    async def get_last_commission(
        self,
        affiliate_id: int,
    ) -> Optional[AffiliateCommission]:
        """Última comissão recebida"""
        db = await get_db()
        try:
            result = await db.execute(
                select(AffiliateCommission)
                .where(AffiliateCommission.affiliate_id == affiliate_id)
                .order_by(AffiliateCommission.id.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def create_commission(
        self,
        affiliate_id: int,
        referred_id: int,
        payment_id: int,
        deposit_amount: float,
        commission_rate: float,
        commission_amount: float,
    ) -> AffiliateCommission:
        """Cria registro de comissão"""
        db = await get_db()
        try:
            commission = AffiliateCommission(
                affiliate_id=affiliate_id,
                referred_id=referred_id,
                payment_id=payment_id,
                deposit_amount=deposit_amount,
                commission_rate=commission_rate,
                commission_amount=commission_amount,
                status="credited",
            )
            db.add(commission)
            await db.commit()
            await db.refresh(commission)
            
            return commission
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def get_commission_history(
        self,
        affiliate_id: int,
        limit: int = 20,
    ) -> List[AffiliateCommission]:
        """Histórico de comissões"""
        db = await get_db()
        try:
            result = await db.execute(
                select(AffiliateCommission)
                .where(AffiliateCommission.affiliate_id == affiliate_id)
                .order_by(AffiliateCommission.id.desc())
                .limit(limit)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_referred_deposits(self, referred_id: int) -> float:
        """Total de depósitos de um indicado"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(Payment.amount))
                .where(
                    and_(
                        Payment.user_id == referred_id,
                        Payment.status == "approved",
                    )
                )
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
    
    async def get_commission_by_referred(
        self,
        affiliate_id: int,
        referred_id: int,
    ) -> float:
        """Comissão gerada por um indicado específico"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(AffiliateCommission.commission_amount))
                .where(
                    and_(
                        AffiliateCommission.affiliate_id == affiliate_id,
                        AffiliateCommission.referred_id == referred_id,
                        AffiliateCommission.status == "credited",
                    )
                )
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
    
    async def get_total_affiliates(self) -> int:
        """Total de afiliados ativos"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.count(func.distinct(Affiliate.referrer_id)))
            )
            return result.scalar() or 0
        finally:
            await db.close()
    
    async def get_total_commissions_all(self) -> float:
        """Total de todas as comissões pagas"""
        db = await get_db()
        try:
            result = await db.execute(
                select(func.sum(AffiliateCommission.commission_amount))
                .where(AffiliateCommission.status == "credited")
            )
            return result.scalar() or 0.0
        finally:
            await db.close()
    
    async def get_affiliate_relation(
        self,
        referrer_id: int,
        referred_id: int,
    ) -> Optional[Affiliate]:
        """Busca relação de afiliado"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Affiliate)
                .where(
                    and_(
                        Affiliate.referrer_id == referrer_id,
                        Affiliate.referred_id == referred_id,
                    )
                )
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
