"""
Repositório de Configurações do Sistema
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select

from database.models.system_setting import SystemSetting
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class SettingRepository(BaseRepository[SystemSetting]):
    """Repositório para configurações do sistema"""
    
    def __init__(self):
        super().__init__(SystemSetting)
    
    async def get_by_key(self, key: str) -> Optional[SystemSetting]:
        """Busca configuração pela chave"""
        db = await get_db()
        try:
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_value(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração"""
        setting = await self.get_by_key(key)
        
        if not setting:
            return default
        
        # Converte baseado no tipo
        value_type = setting.value_type
        
        if value_type == "integer":
            return int(setting.value) if setting.value else default
        elif value_type == "float":
            return float(setting.value) if setting.value else default
        elif value_type == "boolean":
            return setting.value.lower() in ["true", "1", "yes"]
        elif value_type == "json":
            import json
            return json.loads(setting.value) if setting.value else default
        else:
            return setting.value if setting.value else default
    
    async def set_value(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str = None,
        category: str = "general",
        updated_by: int = None,
    ) -> SystemSetting:
        """Define valor de configuração"""
        db = await get_db()
        try:
            existing = await self.get_by_key(key)
            
            # Converte valor para string
            if isinstance(value, (dict, list)):
                import json
                str_value = json.dumps(value)
                value_type = "json"
            elif isinstance(value, bool):
                str_value = str(value).lower()
                value_type = "boolean"
            else:
                str_value = str(value)
            
            if existing:
                existing.value = str_value
                existing.value_type = value_type
                existing.updated_at = datetime.utcnow()
                if description:
                    existing.description = description
                if updated_by:
                    existing.updated_by = updated_by
            else:
                existing = SystemSetting(
                    key=key,
                    value=str_value,
                    value_type=value_type,
                    description=description,
                    category=category,
                    updated_by=updated_by,
                )
                db.add(existing)
            
            await db.commit()
            await db.refresh(existing)
            
            return existing
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def get_all_settings(self) -> List[SystemSetting]:
        """Todas as configurações"""
        db = await get_db()
        try:
            result = await db.execute(
                select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_settings_by_category(self, category: str) -> List[SystemSetting]:
        """Configurações por categoria"""
        db = await get_db()
        try:
            result = await db.execute(
                select(SystemSetting)
                .where(SystemSetting.category == category)
                .order_by(SystemSetting.key)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_all_as_dict(self) -> Dict[str, Any]:
        """Todas configurações como dicionário"""
        settings = await self.get_all_settings()
        
        result = {}
        for setting in settings:
            result[setting.key] = setting.value
        
        return result
