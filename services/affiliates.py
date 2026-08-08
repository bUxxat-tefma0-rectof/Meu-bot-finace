"""
Serviço de Afiliados
Gerencia indicações, comissões e estatísticas
"""

import logging
from typing import Dict, Any, List, Optional

from config import settings
from database.repositories.affiliate_repository import AffiliateRepository
from database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AffiliateService:
    """
    Serviço para programa de afiliados
    """
    
    def __init__(self):
        self.affiliate_repo = AffiliateRepository()
        self.user_repo = UserRepository()
    
    async def get_affiliate_info(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca informações do afiliado
        
        Args:
            telegram_id: ID do afiliado
            
        Returns:
            Dados do afiliado
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        total_referrals = await self.affiliate_repo.get_referral_count(telegram_id)
        total_earnings = await self.affiliate_repo.get_total_commissions(telegram_id)
        
        # Saldo disponível (já está no saldo do usuário)
        available_balance = user.affiliate_earnings
        
        last_commission = await self.affiliate_repo.get_last_commission(telegram_id)
        
        return {
            "telegram_id": telegram_id,
            "total_referrals": total_referrals,
            "total_earnings": total_earnings,
            "available_balance": available_balance,
            "last_commission_date": (
                last_commission.created_at.strftime("%d/%m/%Y")
                if last_commission else "N/A"
            ),
            "commission_rate": settings.AFFILIATE_COMMISSION_PERCENT,
            "min_deposit": settings.AFFILIATE_MIN_DEPOSIT_FOR_COMMISSION,
            "affiliate_link": f"https://t.me/{settings.BOT_USERNAME}?start={telegram_id}",
        }
    
    async def get_referrals(self, telegram_id: int) -> List[Dict]:
        """
        Lista indicados do afiliado
        
        Args:
            telegram_id: ID do afiliado
            
        Returns:
            Lista de indicados
        """
        referrals = await self.affiliate_repo.get_referrals(telegram_id)
        
        result = []
        for ref in referrals:
            referred_user = await self.user_repo.get_by_telegram_id(ref.referred_id)
            
            # Total de depósitos do indicado
            total_deposits = await self.affiliate_repo.get_referred_deposits(
                ref.referred_id
            )
            
            # Comissão gerada por este indicado
            commission_generated = await self.affiliate_repo.get_commission_by_referred(
                telegram_id,
                ref.referred_id,
            )
            
            result.append({
                "telegram_id": ref.referred_id,
                "first_name": referred_user.first_name if referred_user else "Usuário",
                "username": referred_user.username if referred_user else "",
                "total_deposits": total_deposits,
                "commission_generated": commission_generated,
                "joined_at": ref.created_at.strftime("%d/%m/%Y") if ref.created_at else "N/A",
            })
        
        return result
    
    async def get_commission_history(
        self,
        telegram_id: int,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Histórico de comissões
        
        Args:
            telegram_id: ID do afiliado
            limit: Limite de registros
            
        Returns:
            Lista de comissões
        """
        commissions = await self.affiliate_repo.get_commission_history(
            telegram_id,
            limit=limit,
        )
        
        result = []
        for com in commissions:
            referred_user = await self.user_repo.get_by_telegram_id(com.referred_id)
            
            result.append({
                "id": com.id,
                "date": com.created_at.strftime("%d/%m/%Y %H:%M") if com.created_at else "N/A",
                "referred_name": referred_user.first_name if referred_user else "Usuário",
                "deposit_value": com.deposit_amount,
                "commission_rate": com.commission_rate,
                "commission_value": com.commission_amount,
                "status": com.status,
            })
        
        return result
    
    async def get_total_affiliates(self) -> int:
        """Total de afiliados ativos"""
        return await self.affiliate_repo.get_total_affiliates()
    
    async def get_total_commissions(self) -> float:
        """Total de comissões pagas"""
        return await self.affiliate_repo.get_total_commissions_all()
    
    async def create_affiliate(
        self,
        referrer_id: int,
        referred_id: int,
    ) -> Dict[str, Any]:
        """
        Cria relação de afiliado
        
        Args:
            referrer_id: Quem indicou
            referred_id: Quem foi indicado
            
        Returns:
            Resultado
        """
        try:
            # Verifica se já existe
            existing = await self.affiliate_repo.get_affiliate_relation(
                referrer_id,
                referred_id,
            )
            
            if existing:
                return {"success": False, "error": "Relação já existe"}
            
            # Não pode se auto-indicar
            if referrer_id == referred_id:
                return {"success": False, "error": "Não pode se auto-indicar"}
            
            affiliate = await self.affiliate_repo.create_affiliate(
                referrer_id=referrer_id,
                referred_id=referred_id,
            )
            
            # Atualiza contador do afiliado
            referrer = await self.user_repo.get_by_telegram_id(referrer_id)
            if referrer:
                await self.user_repo.update(
                    referrer.id,
                    total_referrals=referrer.total_referrals + 1,
                )
            
            logger.info(f"Afiliado registrado: {referrer_id} -> {referred_id}")
            
            return {"success": True, "affiliate_id": affiliate.id}
            
        except Exception as e:
            logger.error(f"Erro ao criar afiliado: {e}")
            return {"success": False, "error": str(e)}
