"""
Conexão e gerenciamento do banco de dados
Suporte a SQLite (dev) e PostgreSQL (produção)
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from config import settings

logger = logging.getLogger(__name__)

# Engine global
engine: AsyncEngine = None

# Factory de sessões
async_session_factory: async_sessionmaker = None

# Base para modelos ORM
Base = declarative_base()


async def init_db() -> None:
    """
    Inicializa a conexão com o banco de dados
    Deve ser chamado uma vez no início da aplicação
    """
    global engine, async_session_factory
    
    logger.info(f"Inicializando banco de dados: {settings.DATABASE_URL[:50]}...")
    
    # Configurações específicas por driver
    connect_args = {}
    
    if "sqlite" in settings.DATABASE_URL:
        # SQLite - arquivo local
        connect_args["check_same_thread"] = False
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        
        # Habilita WAL mode e foreign keys no SQLite
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    
    elif "postgresql" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL:
        # PostgreSQL
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    else:
        # Outros bancos
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
    
    # Cria factory de sessões
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("Engine do banco de dados criada com sucesso!")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Retorna uma sessão do banco de dados
    Uso: async for session in get_session():
    """
    if not async_session_factory:
        raise RuntimeError("Banco de dados não inicializado. Chame init_db() primeiro.")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Erro na sessão do banco: {e}")
            raise
        finally:
            await session.close()


async def get_db() -> AsyncSession:
    """
    Retorna uma sessão direta do banco de dados
    Uso: db = await get_db()
    Lembre-se de fechar: await db.close()
    """
    if not async_session_factory:
        raise RuntimeError("Banco de dados não inicializado. Chame init_db() primeiro.")
    
    session = async_session_factory()
    return session


async def create_tables() -> None:
    """
    Cria todas as tabelas definidas nos modelos
    Deve ser chamado após init_db()
    """
    if not engine:
        raise RuntimeError("Engine não inicializada. Chame init_db() primeiro.")
    
    async with engine.begin() as conn:
        # Importa todos os modelos para registrar no Base
        from database.models import (  # noqa: F401
            user, admin, category, product, stock_item,
            order, order_item, payment, pix_transaction,
            affiliate, affiliate_commission, button,
            message_template, system_setting, notification,
            media, audit_log, user_session
        )
        
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Tabelas criadas/verificadas com sucesso!")


async def drop_tables() -> None:
    """
    Remove todas as tabelas (CUIDADO!)
    Apenas para desenvolvimento
    """
    if not engine:
        raise RuntimeError("Engine não inicializada.")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.warning("TODAS as tabelas foram removidas!")


async def check_connection() -> bool:
    """
    Verifica se a conexão com o banco está ativa
    """
    if not engine:
        return False
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Falha na conexão com banco: {e}")
        return False


async def close_db() -> None:
    """
    Fecha a conexão com o banco de dados
    """
    global engine, async_session_factory
    
    if engine:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Conexão com banco de dados fechada.")


def get_engine() -> AsyncEngine:
    """Retorna a engine atual"""
    if not engine:
        raise RuntimeError("Engine não inicializada.")
    return engine
