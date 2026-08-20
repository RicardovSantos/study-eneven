"""Aplicação FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth as auth_v1
from app.api.v1 import dashboard as dashboard_v1
from app.api.v1 import materias as materias_v1
from app.api.v1 import objetivos as objetivos_v1
from app.api.v1 import sessoes as sessoes_v1
from app.core.config import get_settings
from app.db.session import engine

s = get_settings()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=f"{s.APP_NAME} API",
    version="0.1.0",
    lifespan=ciclo_de_vida,
    # A documentação interativa fica fora do ar em produção: ela expõe
    # a superfície inteira da API para quem não precisa vê-la.
    docs_url=None if s.producao else "/api/docs",
    redoc_url=None,
    openapi_url=None if s.producao else "/api/openapi.json",
)

if s.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,       # o refresh token viaja em cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(auth_v1.router, prefix=s.API_PREFIX)
app.include_router(materias_v1.router, prefix=s.API_PREFIX)
app.include_router(objetivos_v1.router, prefix=s.API_PREFIX)
app.include_router(sessoes_v1.router, prefix=s.API_PREFIX)
app.include_router(dashboard_v1.router, prefix=s.API_PREFIX)


@app.get("/health/live", tags=["saúde"])
async def vivo() -> dict[str, str]:
    """O processo respondeu. Não toca no banco de propósito.

    Se o banco cair, este endpoint continua verde e o orquestrador não
    reinicia um container que está saudável — reiniciar não traria o
    banco de volta.
    """
    return {"status": "vivo"}


@app.get("/health/ready", tags=["saúde"])
async def pronto() -> dict[str, object]:
    """Pronto para receber tráfego: exige o banco respondendo."""
    checagens: dict[str, object] = {}
    try:
        async with engine.connect() as conexao:
            await conexao.execute(text("SELECT 1"))
        checagens["postgres"] = "ok"
    except Exception as e:
        checagens["postgres"] = f"falhou: {type(e).__name__}"

    tudo_ok = all(v == "ok" for v in checagens.values())
    return {"status": "pronto" if tudo_ok else "indisponivel", "checagens": checagens}
