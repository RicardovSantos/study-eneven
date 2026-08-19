"""Configuração da aplicação.

Tudo vem de variável de ambiente. Nenhum valor sensível tem padrão: se
faltar, a aplicação recusa a subir em vez de rodar com algo inseguro.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "DevLog"
    APP_BASE_URL: str = "http://localhost:5173"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: PostgresDsn
    REDIS_URL: str = "redis://localhost:6379/0"

    # Sem padrão de propósito: uma chave fraca aqui compromete todas as sessões.
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 30

    # Deixe em branco para o padrão seguir o ambiente: um cookie Secure
    # não é enviado por HTTP, então em desenvolvimento (e nos testes,
    # que rodam sobre http) ele quebraria o refresh silenciosamente.
    COOKIE_SECURE: bool | None = None
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    CORS_ORIGINS: list[str] = []

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_PATH: str = "/app/storage"
    MAX_CAPTURE_BYTES: int = 3 * 1024 * 1024

    CAPTURE_INTERVAL_SECONDS: int = 480          # 8 minutos
    CAPTURE_RETENTION_DAYS: int = 15
    SESSION_HEARTBEAT_SECONDS: int = 30
    SESSION_HEARTBEAT_TIMEOUT_SECONDS: int = 90
    LOCATION_WITH_CAPTURE: bool = True

    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _lista_de_origens(cls, v: str | list[str]) -> list[str]:
        """Aceita "https://a.com,https://b.com" além de lista JSON."""
        if isinstance(v, str):
            return [origem.strip() for origem in v.split(",") if origem.strip()]
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _chave_nao_pode_ser_exemplo(cls, v: str) -> str:
        proibidas = {"changeme", "secret", "troque-me", "mudar"}
        if v.lower() in proibidas:
            raise ValueError("JWT_SECRET_KEY está com um valor de exemplo")
        return v

    @property
    def producao(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cookie_secure(self) -> bool:
        """Secure em produção; configurável para os demais ambientes."""
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.producao


@lru_cache
def get_settings() -> Settings:
    """Cacheado: a configuração é lida uma vez por processo."""
    return Settings()  # type: ignore[call-arg]
