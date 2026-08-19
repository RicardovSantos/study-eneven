import os

# Configuração mínima antes de qualquer import da aplicação: get_settings
# é cacheado, então precisa encontrar o ambiente já montado.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://teste:teste@localhost:5432/devlog_teste")
os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-com-mais-de-32-caracteres-aqui")
os.environ.setdefault("ENVIRONMENT", "development")
