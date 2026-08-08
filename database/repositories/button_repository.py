"""
Repositório de Botões do Menu
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, and_

from database.models.button import Button
from database.repositories.base_repository import BaseRepository
from database.connection import get_db

logger = logging.getLogger(__name__)


class ButtonRepository(BaseRepository[Button]):
    """Repositório para botões customizáveis do menu"""
    
    def __init__(self):
        super().__init__(Button)
    
    async def get_active_buttons(
        self,
        parent_menu: str = "main",
    ) -> List[Button]:
        """
        Busca botões ativos e visíveis de um menu
        
        Args:
            parent_menu: Menu pai (main, catalog, etc)
            
        Returns:
            Lista de botões ordenados
        """
        db = await get_db()
        try:
            result = await db.execute(
                select(Button)
                .where(
                    and_(
                        Button.parent_menu == parent_menu,
                        Button.is_active == True,
                        Button.is_visible == True,
                    )
                )
                .order_by(Button.position, Button.id)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_all_buttons(self) -> List[Button]:
        """Todos os botões (admin)"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Button).order_by(Button.parent_menu, Button.position)
            )
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_button_by_name(self, name: str) -> Optional[Button]:
        """Busca botão pelo nome"""
        db = await get_db()
        try:
            result = await db.execute(
                select(Button).where(Button.name == name)
            )
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def create_button(
        self,
        name: str,
        label: str,
        action: str,
        emoji: str = None,
        action_data: str = None,
        position: int = 0,
        row: int = 0,
        parent_menu: str = "main",
    ) -> Button:
        """Cria novo botão"""
        db = await get_db()
        try:
            button = Button(
                name=name,
                label=label,
                emoji=emoji,
                action=action,
                action_data=action_data,
                position=position,
                row=row,
                parent_menu=parent_menu,
            )
            db.add(button)
            await db.commit()
            await db.refresh(button)
            
            logger.info(f"Botão criado: {name} -> {action}")
            
            return button
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await db.close()
    
    async def toggle_button(self, button_id: int) -> Optional[Button]:
        """Ativa/desativa botão"""
        button = await self.get_by_id(button_id)
        if not button:
            return None
        
        return await self.update(button_id, is_active=not button.is_active)
    
    async def toggle_visibility(self, button_id: int) -> Optional[Button]:
        """Mostra/oculta botão"""
        button = await self.get_by_id(button_id)
        if not button:
            return None
        
        return await self.update(button_id, is_visible=not button.is_visible)
    
    async def reorder_buttons(
        self,
        button_order: List[dict],
    ) -> bool:
        """
        Reordena botões
        
        Args:
            button_order: Lista de {"id": int, "position": int}
        """
        db = await get_db()
        try:
            for item in button_order:
                await db.execute(
                    __import__('sqlalchemy').update(Button)
                    .where(Button.id == item["id"])
                    .values(position=item["position"])
                )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            return False
        finally:
            await db.close()
    
    async def duplicate_button(self, button_id: int) -> Optional[Button]:
        """Duplica um botão"""
        original = await self.get_by_id(button_id)
        if not original:
            return None
        
        return await self.create_button(
            name=f"{original.name}_copy",
            label=f"{original.label} (cópia)",
            action=original.action,
            emoji=original.emoji,
            action_data=original.action_data,
            position=original.position + 1,
            row=original.row,
            parent_menu=original.parent_menu,
        )
