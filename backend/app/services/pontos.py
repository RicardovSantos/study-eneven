"""Crédito de pontos.

Regra da seção 10.1: um minuto válido de estudo vale um ponto. Tarefa sem
cronômetro vale os pontos fixos configurados pelo responsável.

Três proteções contra pontuação inflada, todas no servidor:

1. **Idempotência.** Cada crédito carrega uma chave derivada do evento
   que o originou. O reenvio de uma finalização de sessão não credita de
   novo — a restrição única no banco recusa.
2. **Teto diário por objetivo.** Deixar o cronômetro ligado a noite toda
   não rende pontos ilimitados.
3. **Só minutos verificados, para dependentes.** Sessão sem captura
   funcionando não vira ponto para quem tem responsável.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrigemPontos, PapelFamiliar, TipoObjetivo
from app.models.objetivos import Objetivo
from app.models.pontos import LancamentoPontos

SEGUNDOS_POR_PONTO = 60


def minutos_que_contam(
    *, segundos_validos: int, segundos_verificados: int, papel: PapelFamiliar | None
) -> int:
    """Quanto tempo vira ponto.

    Dependente pontua só o tempo verificado; responsável pontua o tempo
    válido. Segundos incompletos são descartados aqui, mas o resto fica
    guardado na sessão — então o minuto se completa na próxima vez, sem
    perder nada (seção 10.1).
    """
    base = segundos_verificados if papel == PapelFamiliar.DEPENDENTE else segundos_validos
    return max(0, base) // SEGUNDOS_POR_PONTO


async def creditados_hoje(
    sessao: AsyncSession, *, beneficiario_id: UUID, objetivo_id: UUID, dia: date | None = None
) -> int:
    dia = dia or date.today()
    inicio = datetime.combine(dia, datetime.min.time(), tzinfo=UTC)
    r = await sessao.execute(
        select(func.coalesce(func.sum(LancamentoPontos.pontos), 0)).where(
            LancamentoPontos.beneficiario_id == beneficiario_id,
            LancamentoPontos.objetivo_id == objetivo_id,
            LancamentoPontos.criado_em >= inicio,
            LancamentoPontos.criado_em < inicio + timedelta(days=1),
        )
    )
    return int(r.scalar_one() or 0)


async def creditar(
    sessao: AsyncSession,
    *,
    beneficiario_id: UUID,
    familia_id: UUID,
    objetivo: Objetivo,
    pontos: int,
    origem: OrigemPontos,
    chave_idempotencia: str,
    sessao_id: UUID | None = None,
    ocorrencia_id: UUID | None = None,
    descricao: str | None = None,
    criado_por_id: UUID | None = None,
    agora: datetime | None = None,
) -> LancamentoPontos | None:
    """Lança pontos no livro-razão. Devolve None se nada foi creditado.

    O horário do lançamento é o momento real do estudo, e não a data
    prevista da ocorrência: uma aula adiantada pontua no dia em que foi
    feita (seção 9).
    """
    # Zero não vira linha (o CHECK do banco recusaria), mas negativo sim:
    # estorno é um lançamento, não uma exclusão.
    if pontos == 0:
        return None

    ja = await sessao.execute(
        select(LancamentoPontos).where(
            LancamentoPontos.chave_idempotencia == chave_idempotencia
        )
    )
    if ja.scalar_one_or_none() is not None:
        return None

    agora = agora or datetime.now(UTC)

    # O teto diário só limita crédito. Estorno não é afetado por ele.
    if pontos > 0 and objetivo.limite_pontos_dia:
        gastos = await creditados_hoje(
            sessao,
            beneficiario_id=beneficiario_id,
            objetivo_id=objetivo.id,
            dia=agora.date(),
        )
        disponivel = max(0, objetivo.limite_pontos_dia - gastos)
        pontos = min(pontos, disponivel)
        if pontos <= 0:
            return None

    lancamento = LancamentoPontos(
        beneficiario_id=beneficiario_id,
        familia_id=familia_id,
        objetivo_id=objetivo.id,
        materia_id=objetivo.materia_id,
        sessao_id=sessao_id,
        ocorrencia_id=ocorrencia_id,
        pontos=pontos,
        origem=origem,
        descricao=descricao,
        criado_por_id=criado_por_id,
        criado_em=agora,
    )
    sessao.add(lancamento)
    await sessao.flush()
    return lancamento


async def total_de(sessao: AsyncSession, *, beneficiario_id: UUID) -> int:
    """Soma do livro-razão. Não existe campo 'total' para desincronizar."""
    r = await sessao.execute(
        select(func.coalesce(func.sum(LancamentoPontos.pontos), 0)).where(
            LancamentoPontos.beneficiario_id == beneficiario_id
        )
    )
    return int(r.scalar_one() or 0)


async def total_por_materia(sessao: AsyncSession, *, beneficiario_id: UUID) -> dict[UUID, int]:
    r = await sessao.execute(
        select(LancamentoPontos.materia_id, func.sum(LancamentoPontos.pontos))
        .where(LancamentoPontos.beneficiario_id == beneficiario_id)
        .group_by(LancamentoPontos.materia_id)
    )
    return {materia: int(total) for materia, total in r if materia is not None}


def pontos_de_tarefa(objetivo: Objetivo) -> int:
    """Tarefa sem cronômetro usa o valor fixo do objetivo."""
    if objetivo.tipo != TipoObjetivo.TAREFA:
        return 0
    return objetivo.pontos_fixos or 0
