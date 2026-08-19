"""Conclusão e adiantamento de ocorrências.

O adiantamento é a parte que a versão em localStorage não conseguia
fazer, porque lá a recorrência era um contador agregado. Com ocorrência
como linha própria, "adiantar a aula de amanhã" é concluir a linha de
amanhã hoje — ela guarda a data prevista e a data real, e por isso:

- não reaparece como pendente na data original;
- pontua no dia em que o estudo realmente aconteceu;
- não conta um dia futuro na sequência de dias estudando;
- aparece no dia previsto como "concluída antecipadamente".
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontrado, SemPermissao
from app.models.enums import (
    MomentoConclusao,
    OrigemPontos,
    PapelFamiliar,
    StatusObjetivo,
    StatusOcorrencia,
    TipoObjetivo,
)
from app.models.objetivos import Objetivo, Ocorrencia
from app.models.pontos import LancamentoPontos
from app.services import pontos as servico_pontos


@dataclass
class Conclusao:
    ocorrencia: Ocorrencia
    pontos_creditados: int
    momento: MomentoConclusao


def _momento(prevista: date, hoje: date) -> tuple[MomentoConclusao, int]:
    if hoje < prevista:
        return MomentoConclusao.ADIANTADA, (prevista - hoje).days
    if hoje > prevista:
        return MomentoConclusao.ATRASADA, 0
    return MomentoConclusao.NO_PRAZO, 0


async def proxima_pendente(
    sessao: AsyncSession, objetivo_id: UUID, depois_de: date
) -> Ocorrencia | None:
    """Próxima obrigação da fila, em ordem de data.

    A ordem importa: a especificação exige respeitar a sequência das
    aulas. Não dá para pular a aula 12 e adiantar a 13.
    """
    r = await sessao.execute(
        select(Ocorrencia)
        .where(
            Ocorrencia.objetivo_id == objetivo_id,
            Ocorrencia.prevista_para > depois_de,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
        )
        .order_by(Ocorrencia.prevista_para)
        .limit(1)
    )
    return r.scalar_one_or_none()


async def adiantadas_em_aberto(
    sessao: AsyncSession, objetivo_id: UUID, hoje: date
) -> int:
    """Quantas ocorrências futuras já foram concluídas antecipadamente.

    É o que limita o adiantamento: sem isso alguém faria o mês inteiro
    numa tarde e o objetivo perderia o sentido de constância.
    """
    r = await sessao.execute(
        select(func.count())
        .select_from(Ocorrencia)
        .where(
            Ocorrencia.objetivo_id == objetivo_id,
            Ocorrencia.prevista_para > hoje,
            Ocorrencia.status == StatusOcorrencia.CONCLUIDA,
        )
    )
    return int(r.scalar_one() or 0)


async def pode_adiantar(
    sessao: AsyncSession, objetivo: Objetivo, ocorrencia: Ocorrencia, hoje: date
) -> tuple[bool, str]:
    """Devolve (pode, motivo). O motivo vai para a tela quando não pode."""
    if not objetivo.permite_adiantar:
        return False, "Este objetivo não está configurado para adiantamento."

    if ocorrencia.prevista_para <= hoje:
        return True, ""      # não é adiantamento; é a obrigação de hoje

    # Exige que nada esteja pendente para trás — a obrigação atual vem
    # antes da próxima (seção 9).
    r = await sessao.execute(
        select(func.count())
        .select_from(Ocorrencia)
        .where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.prevista_para <= hoje,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
        )
    )
    if int(r.scalar_one() or 0) > 0:
        return False, "Conclua a atividade de hoje antes de adiantar a próxima."

    anterior = await sessao.execute(
        select(func.count())
        .select_from(Ocorrencia)
        .where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.prevista_para > hoje,
            Ocorrencia.prevista_para < ocorrencia.prevista_para,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
        )
    )
    if int(anterior.scalar_one() or 0) > 0:
        return False, "Existe uma atividade anterior nesta fila."

    ja_adiantadas = await adiantadas_em_aberto(sessao, objetivo.id, hoje)
    if ja_adiantadas >= objetivo.max_adiantamentos:
        return False, (
            f"Você já adiantou {ja_adiantadas} atividade(s); "
            f"o limite deste objetivo é {objetivo.max_adiantamentos}."
        )

    return True, ""


async def registrar_progresso(
    sessao: AsyncSession, ocorrencia: Ocorrencia, quantidade: int
) -> Ocorrencia:
    """Soma tempo (minutos) ou repetições ao que já foi feito."""
    if quantidade <= 0:
        return ocorrencia
    ocorrencia.realizado = (ocorrencia.realizado or 0) + quantidade
    await sessao.flush()
    return ocorrencia


async def concluir(
    sessao: AsyncSession,
    *,
    ocorrencia: Ocorrencia,
    objetivo: Objetivo,
    familia_id: UUID,
    papel: PapelFamiliar | None,
    minutos_verificados: int = 0,
    minutos_validos: int = 0,
    sessao_estudo_id: UUID | None = None,
    hoje: date | None = None,
    agora: datetime | None = None,
) -> Conclusao:
    """Fecha a ocorrência e credita os pontos.

    A chave de idempotência sai da própria ocorrência: concluir duas
    vezes não credita duas vezes, mesmo que a chamada se repita por
    reenvio da rede.
    """
    hoje = hoje or date.today()
    agora = agora or datetime.now(UTC)

    if ocorrencia.status == StatusOcorrencia.CONCLUIDA:
        return Conclusao(ocorrencia, 0, ocorrencia.momento_conclusao or MomentoConclusao.NO_PRAZO)

    if ocorrencia.prevista_para > hoje:
        pode, motivo = await pode_adiantar(sessao, objetivo, ocorrencia, hoje)
        if not pode:
            raise SemPermissao(motivo)

    momento, dias = _momento(ocorrencia.prevista_para, hoje)

    ocorrencia.status = StatusOcorrencia.CONCLUIDA
    ocorrencia.concluida_em = agora
    ocorrencia.momento_conclusao = momento
    ocorrencia.dias_adiantados = dias
    ocorrencia.sessao_conclusao_id = sessao_estudo_id

    if objetivo.tipo == TipoObjetivo.ESTUDO:
        pontos = servico_pontos.minutos_que_contam(
            segundos_validos=minutos_validos * 60,
            segundos_verificados=minutos_verificados * 60,
            papel=papel,
        )
    else:
        pontos = servico_pontos.pontos_de_tarefa(objetivo)

    lancamento = await servico_pontos.creditar(
        sessao,
        beneficiario_id=ocorrencia.titular_id,
        familia_id=familia_id,
        objetivo=objetivo,
        pontos=pontos,
        origem=(
            OrigemPontos.SESSAO_ESTUDO
            if objetivo.tipo == TipoObjetivo.ESTUDO
            else OrigemPontos.TAREFA
        ),
        chave_idempotencia=f"ocorrencia:{ocorrencia.id}",
        sessao_id=sessao_estudo_id,
        ocorrencia_id=ocorrencia.id,
        descricao=objetivo.nome,
        agora=agora,
    )

    await _fechar_objetivo_se_completo(sessao, objetivo)
    await sessao.flush()
    return Conclusao(ocorrencia, lancamento.pontos if lancamento else 0, momento)


async def _fechar_objetivo_se_completo(sessao: AsyncSession, objetivo: Objetivo) -> None:
    """Marca o objetivo como concluído ao bater a meta total do curso."""
    if not objetivo.meta_total:
        return
    r = await sessao.execute(
        select(func.coalesce(func.sum(Ocorrencia.realizado), 0)).where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.status == StatusOcorrencia.CONCLUIDA,
        )
    )
    if int(r.scalar_one() or 0) >= objetivo.meta_total:
        objetivo.status = StatusObjetivo.CONCLUIDO


async def desfazer(
    sessao: AsyncSession, *, ocorrencia: Ocorrencia, objetivo: Objetivo
) -> None:
    """Reabre uma conclusão.

    Os pontos não são apagados: entra um lançamento negativo. O
    livro-razão só cresce, e o estorno fica auditável (seção 10.1).
    """
    if ocorrencia.status != StatusOcorrencia.CONCLUIDA:
        raise NaoEncontrado("Esta atividade não está concluída.")

    r = await sessao.execute(
        select(func.coalesce(func.sum(LancamentoPontos.pontos), 0)).where(
            LancamentoPontos.ocorrencia_id == ocorrencia.id
        )
    )
    creditado = int(r.scalar_one() or 0)

    if creditado != 0:
        await servico_pontos.creditar(
            sessao,
            beneficiario_id=ocorrencia.titular_id,
            familia_id=objetivo.familia_id,
            objetivo=objetivo,
            pontos=-creditado,
            origem=OrigemPontos.AJUSTE_ADMIN,
            chave_idempotencia=f"estorno:{ocorrencia.id}",
            ocorrencia_id=ocorrencia.id,
            descricao=f"Estorno — {objetivo.nome}",
        )

    ocorrencia.status = StatusOcorrencia.PENDENTE
    ocorrencia.concluida_em = None
    ocorrencia.momento_conclusao = None
    ocorrencia.dias_adiantados = 0
    ocorrencia.sessao_conclusao_id = None
    if objetivo.status == StatusObjetivo.CONCLUIDO:
        objetivo.status = StatusObjetivo.ANDAMENTO
    await sessao.flush()
