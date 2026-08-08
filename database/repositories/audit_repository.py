"""
Repositório de Logs de Auditoria
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, and_

from database.models.audit_log import AuditLog
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository[AuditLog]):
    """Repositório para logs de auditoria"""
    
    def __init__(self):
        super().__init__(AuditLog)
    
    async def create_log(
        self,
        admin_id: int,
        action: str,
        entity_type: str,
        entity_id: int = None,
        description: str = None,
        old_value: str = None,
        new_value: str = None,
        admin_name: str = None,
    ) -> AuditLog:
        """Cria um registro de log"""
        db = await get_db()
        try:
            log = AuditLog(
                admin_id=admin_id,
                admin_name=admin_name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                old_value=old_value,
                new_value=new_value,
            )
            db.add(log)
            await db.commit()
            await db.refresh(log)
            return log
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def get_logs(
        self,
        admin_id: int = None,
        entity_type: str = None,
        action: str = None,
        limit: int = 20,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """Busca logs com filtros"""
        db = await get_db()
        try:
            offset = (page - 1) * per_page
            
            query = select(AuditLog)
            count_query = select(func.count(AuditLog.id))
            
            if admin_id:
                query = query.where(AuditLog.admin_id == admin_id)
                count_query = count_query.where(AuditLog.admin_id == admin_id)
            if entity_type:
                query = query.where(AuditLog.entity_type == entity_type)
                count_query = count_query.where(AuditLog.entity_type == entity_type)
            if action:
                query = query.where(AuditLog.action == action)
                count_query = count_query.where(AuditLog.action == action)
            
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            if limit:
                query = query.limit(limit)
            else:
                query = query.limit(per_page).offset(offset)
            
            result = await db.execute(query.order_by(AuditLog.id.desc()))
            logs = result.scalars().all()
            
            return {
                "logs": logs,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page if not limit else 1,
                "page": page,
            }
        finally:
            await db.close()
    
    async def delete_old_logs(self, cutoff: datetime) -> int:
        """Remove logs antigos"""
        db = await get_db()
        try:
            from sqlalchemy import delete
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            await db.commit()
            return result.rowcount
        except Exception as e:
            await db.rollback()
            return 0
        finally:
            await db.close()
