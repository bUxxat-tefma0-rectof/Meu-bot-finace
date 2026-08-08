"""
Serviço de Mídia
Gerencia upload e armazenamento de imagens
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


class MediaService:
    """
    Serviço para gerenciamento de mídia
    
    Utiliza o próprio Telegram como storage
    (File ID) e opcionalmente armazena localmente.
    """
    
    def __init__(self):
        self.media_dir = settings.MEDIA_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Garante que diretórios existam"""
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(self.media_dir / "products", exist_ok=True)
        os.makedirs(self.media_dir / "categories", exist_ok=True)
        os.makedirs(self.media_dir / "banners", exist_ok=True)
        os.makedirs(self.media_dir / "temp", exist_ok=True)
    
    async def save_media(
        self,
        file_id: str,
        file_type: str = "photo",
        category: str = "general",
        name: Optional[str] = None,
        uploaded_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Salva referência de mídia
        
        Args:
            file_id: File ID do Telegram
            file_type: Tipo (photo, video, document)
            category: Categoria da mídia
            name: Nome descritivo
            uploaded_by: ID de quem fez upload
            
        Returns:
            Dados da mídia salva
        """
        try:
            from database.repositories.media_repository import MediaRepository
            
            repo = MediaRepository()
            
            media = await repo.create(
                name=name or f"media_{file_id[:10]}",
                file_id=file_id,
                file_type=file_type,
                media_category=category,
                uploaded_by=uploaded_by,
            )
            
            logger.info(f"Mídia salva: id={media.id}, type={file_type}")
            
            return {"success": True, "media": media.to_dict()}
            
        except Exception as e:
            logger.error(f"Erro ao salvar mídia: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_media(self, media_id: int) -> Optional[Dict]:
        """Busca mídia por ID"""
        try:
            from database.repositories.media_repository import MediaRepository
            repo = MediaRepository()
            
            media = await repo.get_by_id(media_id)
            return media.to_dict() if media else None
        except Exception as e:
            logger.error(f"Erro ao buscar mídia: {e}")
            return None
    
    async def get_media_by_category(self, category: str) -> List[Dict]:
        """Lista mídia por categoria"""
        try:
            from database.repositories.media_repository import MediaRepository
            repo = MediaRepository()
            
            media_list = await repo.get_by_category(category)
            return [m.to_dict() for m in media_list]
        except Exception as e:
            logger.error(f"Erro ao listar mídia: {e}")
            return []
    
    async def delete_media(self, media_id: int, admin_id: int) -> Dict[str, Any]:
        """Remove mídia"""
        try:
            from database.repositories.media_repository import MediaRepository
            repo = MediaRepository()
            
            success = await repo.delete(media_id)
            
            if success:
                return {"success": True}
            
            return {"success": False, "error": "Mídia não encontrada"}
            
        except Exception as e:
            logger.error(f"Erro ao deletar mídia: {e}")
            return {"success": False, "error": str(e)}
    
    async def download_media(self, file_id: str, context) -> Optional[str]:
        """
        Download de arquivo do Telegram
        
        Args:
            file_id: File ID
            context: Contexto do bot
            
        Returns:
            Caminho do arquivo salvo ou None
        """
        try:
            file = await context.bot.get_file(file_id)
            
            # Gera nome único
            ext = file.file_path.split(".")[-1] if "." in file.file_path else "jpg"
            filename = f"{file_id}.{ext}"
            filepath = self.media_dir / "temp" / filename
            
            # Download
            await file.download_to_drive(filepath)
            
            logger.info(f"Arquivo baixado: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Erro ao baixar arquivo: {e}")
            return None
    
    async def get_file_id_from_message(self, message) -> Optional[Dict]:
        """
        Extrai File ID de uma mensagem
        
        Args:
            message: Mensagem do Telegram
            
        Returns:
            Dict com file_id e tipo
        """
        if message.photo:
            # Pega a foto de maior resolução
            return {
                "file_id": message.photo[-1].file_id,
                "file_type": "photo",
            }
        elif message.video:
            return {
                "file_id": message.video.file_id,
                "file_type": "video",
            }
        elif message.document:
            return {
                "file_id": message.document.file_id,
                "file_type": "document",
            }
        elif message.animation:
            return {
                "file_id": message.animation.file_id,
                "file_type": "animation",
            }
        
        return None
