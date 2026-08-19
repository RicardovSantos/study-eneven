"""Engine e sessão do banco."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_s = get_settings()

engine = create_async_engine(
    str(_s.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,      # descarta conexão morta antes de usar
    pool_size=10,
    max_overflow=20,
)

Sessao = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_sessao() -> AsyncGenerator[AsyncSession]:
    """Dependência do FastAPI: uma sessão por requisição.

    Sem commit automático: quem escreve decide quando confirmar, para
    uma requisição que muda várias tabelas ser uma transação só.
    """
    async with Sessao() as sessao:
        try:
            yield sessao
        except Exception:
            await sessao.rollback()
            raise
