import os

# Antes de qualquer import da aplicação: get_settings é cacheado e
# precisa encontrar o ambiente já montado.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://teste:teste@localhost:5432/devlog_teste")
os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-com-mais-de-32-caracteres-aqui")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403


@pytest_asyncio.fixture
async def sessao() -> AsyncSession:
    """Banco limpo por teste.

    SQLite em memória, e não PostgreSQL: a suíte roda em qualquer
    máquina e na CI, sem serviço externo. Os modelos usam tipos com
    variante (app/db/tipos.py), então o esquema criado aqui é o mesmo
    que a migração cria no PostgreSQL — só os tipos nativos mudam.

    O que isto NÃO cobre: comportamento específico do PostgreSQL, como
    enums nativos recusando valor inválido ou índices parciais. Esses
    ficam para os testes de integração contra o banco de verdade,
    pendentes da conexão (P1 em docs/pendencias.md).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)

    fabrica = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with fabrica() as s:
        yield s

    await engine.dispose()
