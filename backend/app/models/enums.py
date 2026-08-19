"""Enums do domínio.

São enums nativos do PostgreSQL: o banco recusa um valor inválido mesmo
que alguém escreva direto por SQL, sem passar pela API.
"""

import enum


class PapelFamiliar(str, enum.Enum):
    ADMIN = "admin"
    DEPENDENTE = "dependent"


class StatusMembro(str, enum.Enum):
    ATIVO = "active"
    SUSPENSO = "suspended"
    REMOVIDO = "removed"


class TipoObjetivo(str, enum.Enum):
    ESTUDO = "study"
    TAREFA = "task"


class Frequencia(str, enum.Enum):
    DIARIA = "daily"
    SEMANAL = "weekly"
    MENSAL = "monthly"
    PERSONALIZADA = "custom"


class StatusObjetivo(str, enum.Enum):
    ANDAMENTO = "in_progress"
    PAUSADO = "paused"
    CONCLUIDO = "completed"
    ARQUIVADO = "archived"


class StatusOcorrencia(str, enum.Enum):
    PENDENTE = "pending"
    CONCLUIDA = "completed"
    PERDIDA = "missed"


class MomentoConclusao(str, enum.Enum):
    NO_PRAZO = "on_time"
    ATRASADA = "late"
    ADIANTADA = "early"


class TipoSessao(str, enum.Enum):
    NORMAL = "normal"
    VERIFICADA = "verified"


class EstadoSessao(str, enum.Enum):
    ATIVA = "active"
    PAUSADA = "paused"
    INTERROMPIDA = "interrupted"
    FINALIZADA = "finished"


class StatusCaptura(str, enum.Enum):
    PENDENTE = "pending"
    RECEBIDA = "received"
    INVALIDA = "invalid"
    EXPIRADA = "expired"


class OrigemPontos(str, enum.Enum):
    SESSAO_ESTUDO = "study_session"
    TAREFA = "task"
    AJUSTE_ADMIN = "admin_adjustment"


class EscopoTrilha(str, enum.Enum):
    TODOS = "all"
    MATERIA = "subject"
    OBJETIVO = "objective"
    CONJUNTO = "set"


class StatusRecompensa(str, enum.Enum):
    BLOQUEADA = "locked"
    DESBLOQUEADA = "unlocked"
    SOLICITADA = "requested"
    ENTREGUE = "delivered"


class Plataforma(str, enum.Enum):
    WEB = "web"
    ANDROID = "android"
