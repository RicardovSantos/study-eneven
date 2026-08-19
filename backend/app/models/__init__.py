"""Importa todos os modelos.

O Alembic descobre as tabelas por `Base.metadata`, que só conhece o que
foi importado. Um modelo fora desta lista some silenciosamente das
migrações — por isso o import é explícito e centralizado.
"""

from app.models.identidade import (  # noqa: F401
    Dispositivo,
    Familia,
    MembroFamilia,
    RefreshToken,
    Usuario,
)
from app.models.objetivos import Materia, Objetivo, Ocorrencia  # noqa: F401
from app.models.pontos import (  # noqa: F401
    DesbloqueioRecompensa,
    LancamentoPontos,
    NivelRecompensa,
    Notificacao,
    RegistroAuditoria,
    TrilhaRecompensa,
)
from app.models.sessoes import (  # noqa: F401
    CapturaTela,
    EventoSessao,
    LocalConhecido,
    LocalizacaoSessao,
    SessaoEstudo,
)
