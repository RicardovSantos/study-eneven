"""Enums do domínio.

São enums nativos do PostgreSQL: o banco recusa um valor inválido mesmo
que alguém escreva direto por SQL, sem passar pela API.
"""

import enum


class PapelFamiliar(enum.StrEnum):
    ADMIN = "admin"
    DEPENDENTE = "dependent"


class StatusMembro(enum.StrEnum):
    ATIVO = "active"
    SUSPENSO = "suspended"
    REMOVIDO = "removed"


class TipoObjetivo(enum.StrEnum):
    ESTUDO = "study"
    TAREFA = "task"


class Frequencia(enum.StrEnum):
    DIARIA = "daily"
    SEMANAL = "weekly"
    MENSAL = "monthly"
    PERSONALIZADA = "custom"


class StatusObjetivo(enum.StrEnum):
    ANDAMENTO = "in_progress"
    PAUSADO = "paused"
    CONCLUIDO = "completed"
    ARQUIVADO = "archived"


class StatusOcorrencia(enum.StrEnum):
    PENDENTE = "pending"
    CONCLUIDA = "completed"
    PERDIDA = "missed"


class MomentoConclusao(enum.StrEnum):
    NO_PRAZO = "on_time"
    ATRASADA = "late"
    ADIANTADA = "early"


class TipoSessao(enum.StrEnum):
    NORMAL = "normal"
    VERIFICADA = "verified"


class EstadoSessao(enum.StrEnum):
    ATIVA = "active"
    PAUSADA = "paused"
    INTERROMPIDA = "interrupted"
    FINALIZADA = "finished"


class StatusCaptura(enum.StrEnum):
    PENDENTE = "pending"
    RECEBIDA = "received"
    INVALIDA = "invalid"
    EXPIRADA = "expired"


class OrigemPontos(enum.StrEnum):
    SESSAO_ESTUDO = "study_session"
    TAREFA = "task"
    AJUSTE_ADMIN = "admin_adjustment"


class EscopoTrilha(enum.StrEnum):
    TODOS = "all"
    MATERIA = "subject"
    OBJETIVO = "objective"
    CONJUNTO = "set"


class StatusRecompensa(enum.StrEnum):
    BLOQUEADA = "locked"
    DESBLOQUEADA = "unlocked"
    SOLICITADA = "requested"
    ENTREGUE = "delivered"


class Plataforma(enum.StrEnum):
    WEB = "web"
    ANDROID = "android"
