"""Métricas dos painéis.

Tudo sai do livro-razão e das ocorrências, por consulta agregada. Não
existe campo "total" guardado em lugar nenhum — assim não há como o
número na tela divergir do que aconteceu de fato.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    EstadoSessao,
    PapelFamiliar,
    StatusMembro,
    StatusObjetivo,
    StatusOcorrencia,
)
from app.models.identidade import MembroFamilia, Usuario
from app.models.objetivos import Materia, Objetivo, Ocorrencia
from app.models.pontos import LancamentoPontos
from app.models.sessoes import SessaoEstudo


def _domingo_da(d: date) -> date:
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _intervalo(dia: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(dia, datetime.min.time(), tzinfo=UTC)
    return inicio, inicio + timedelta(days=1)


@dataclass
class ResumoPessoal:
    usuario_id: UUID
    nome: str
    pontos_totais: int
    pontos_por_materia: dict[str, int] = field(default_factory=dict)
    minutos_hoje: int = 0
    minutos_semana: int = 0
    minutos_mes: int = 0
    sequencia_dias: int = 0
    concluidas_hoje: int = 0
    concluidas_total: int = 0
    atrasadas: int = 0
    pendentes_hoje: int = 0
    estado_sessao: str | None = None


async def minutos_no_periodo(
    sessao: AsyncSession, *, usuario_id: UUID, de: date, ate: date
) -> int:
    """Tempo válido apurado pelo servidor, somado das sessões do período."""
    inicio, _ = _intervalo(de)
    _, fim = _intervalo(ate)
    r = await sessao.execute(
        select(func.coalesce(func.sum(SessaoEstudo.segundos_validos), 0)).where(
            SessaoEstudo.usuario_id == usuario_id,
            SessaoEstudo.iniciada_em >= inicio,
            SessaoEstudo.iniciada_em < fim,
        )
    )
    return int(r.scalar_one() or 0) // 60


async def minutos_por_dia(
    sessao: AsyncSession, *, usuario_id: UUID, de: date, ate: date
) -> dict[date, int]:
    """Série para os gráficos. Dias sem estudo entram com zero."""
    inicio, _ = _intervalo(de)
    _, fim = _intervalo(ate)
    r = await sessao.execute(
        select(SessaoEstudo.iniciada_em, SessaoEstudo.segundos_validos).where(
            SessaoEstudo.usuario_id == usuario_id,
            SessaoEstudo.iniciada_em >= inicio,
            SessaoEstudo.iniciada_em < fim,
        )
    )
    serie = {de + timedelta(days=i): 0 for i in range((ate - de).days + 1)}
    for iniciada, segundos in r:
        dia = (iniciada if iniciada.tzinfo else iniciada.replace(tzinfo=UTC)).date()
        if dia in serie:
            serie[dia] += (segundos or 0) // 60
    return {d: m for d, m in serie.items()}


async def sequencia_de_dias(
    sessao: AsyncSession, *, usuario_id: UUID, hoje: date | None = None, limite: int = 400
) -> int:
    """Dias consecutivos com pontos, contando para trás.

    Sai do livro-razão, e não da agenda: uma aula adiantada pontua no dia
    em que foi feita, então um dia futuro nunca entra na sequência
    (exigência da seção 9).

    O dia de hoje ainda sem pontos não quebra a sequência — só interrompe
    quando o dia termina.
    """
    hoje = hoje or date.today()
    inicio, _ = _intervalo(hoje - timedelta(days=limite))
    _, fim = _intervalo(hoje)

    r = await sessao.execute(
        select(LancamentoPontos.criado_em).where(
            LancamentoPontos.beneficiario_id == usuario_id,
            LancamentoPontos.pontos > 0,
            LancamentoPontos.criado_em >= inicio,
            LancamentoPontos.criado_em < fim,
        )
    )
    dias = {
        (m if m.tzinfo else m.replace(tzinfo=UTC)).date() for (m,) in r
    }
    if not dias:
        return 0

    cursor = hoje if hoje in dias else hoje - timedelta(days=1)
    total = 0
    while cursor in dias and total < limite:
        total += 1
        cursor -= timedelta(days=1)
    return total


async def pontos_por_materia(
    sessao: AsyncSession, *, usuario_id: UUID
) -> dict[str, int]:
    r = await sessao.execute(
        select(Materia.nome, func.sum(LancamentoPontos.pontos))
        .join(Materia, Materia.id == LancamentoPontos.materia_id)
        .where(LancamentoPontos.beneficiario_id == usuario_id)
        .group_by(Materia.nome)
    )
    return {nome: int(total) for nome, total in r if total}


async def resumo_pessoal(
    sessao: AsyncSession, *, usuario: Usuario, hoje: date | None = None
) -> ResumoPessoal:
    hoje = hoje or date.today()
    domingo = _domingo_da(hoje)
    primeiro_do_mes = hoje.replace(day=1)

    total = await sessao.execute(
        select(func.coalesce(func.sum(LancamentoPontos.pontos), 0)).where(
            LancamentoPontos.beneficiario_id == usuario.id
        )
    )

    contagem = await sessao.execute(
        select(Ocorrencia.status, func.count())
        .where(Ocorrencia.titular_id == usuario.id)
        .group_by(Ocorrencia.status)
    )
    por_status = {s: int(n) for s, n in contagem}

    concluidas_hoje = await sessao.execute(
        select(func.count()).select_from(Ocorrencia).where(
            Ocorrencia.titular_id == usuario.id,
            Ocorrencia.status == StatusOcorrencia.CONCLUIDA,
            Ocorrencia.concluida_em >= _intervalo(hoje)[0],
            Ocorrencia.concluida_em < _intervalo(hoje)[1],
        )
    )
    pendentes_hoje = await sessao.execute(
        select(func.count()).select_from(Ocorrencia).where(
            Ocorrencia.titular_id == usuario.id,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
            Ocorrencia.prevista_para == hoje,
        )
    )

    sessao_aberta = await sessao.execute(
        select(SessaoEstudo.estado).where(
            SessaoEstudo.usuario_id == usuario.id,
            SessaoEstudo.estado.in_(
                [EstadoSessao.ATIVA, EstadoSessao.PAUSADA, EstadoSessao.INTERROMPIDA]
            ),
        ).limit(1)
    )
    estado = sessao_aberta.scalar_one_or_none()

    return ResumoPessoal(
        usuario_id=usuario.id,
        nome=usuario.nome_exibicao,
        pontos_totais=int(total.scalar_one() or 0),
        pontos_por_materia=await pontos_por_materia(sessao, usuario_id=usuario.id),
        minutos_hoje=await minutos_no_periodo(sessao, usuario_id=usuario.id, de=hoje, ate=hoje),
        minutos_semana=await minutos_no_periodo(
            sessao, usuario_id=usuario.id, de=domingo, ate=hoje
        ),
        minutos_mes=await minutos_no_periodo(
            sessao, usuario_id=usuario.id, de=primeiro_do_mes, ate=hoje
        ),
        sequencia_dias=await sequencia_de_dias(sessao, usuario_id=usuario.id, hoje=hoje),
        concluidas_hoje=int(concluidas_hoje.scalar_one() or 0),
        concluidas_total=por_status.get(StatusOcorrencia.CONCLUIDA, 0),
        atrasadas=por_status.get(StatusOcorrencia.PERDIDA, 0),
        pendentes_hoje=int(pendentes_hoje.scalar_one() or 0),
        estado_sessao=estado.value if estado else None,
    )


async def resumo_da_familia(
    sessao: AsyncSession, *, familia_id: UUID, hoje: date | None = None
) -> list[ResumoPessoal]:
    """Um cartão por dependente, para o painel do responsável."""
    r = await sessao.execute(
        select(Usuario)
        .join(MembroFamilia, MembroFamilia.usuario_id == Usuario.id)
        .where(
            MembroFamilia.familia_id == familia_id,
            MembroFamilia.papel == PapelFamiliar.DEPENDENTE,
            MembroFamilia.status == StatusMembro.ATIVO,
        )
        .order_by(Usuario.nome_exibicao)
    )
    return [await resumo_pessoal(sessao, usuario=u, hoje=hoje) for u in r.scalars()]


async def historico(
    sessao: AsyncSession,
    *,
    usuario_id: UUID,
    limite: int = 10,
    deslocamento: int = 0,
) -> list[dict]:
    """Últimas atividades, paginadas.

    A tela mostra dez por padrão e o "ver histórico completo" pagina
    daqui — sem carregar meses de registro de uma vez.
    """
    r = await sessao.execute(
        select(LancamentoPontos, Objetivo.nome)
        .outerjoin(Objetivo, Objetivo.id == LancamentoPontos.objetivo_id)
        .where(LancamentoPontos.beneficiario_id == usuario_id)
        .order_by(LancamentoPontos.criado_em.desc())
        .limit(limite)
        .offset(deslocamento)
    )
    return [
        {
            "id": lancamento.id,
            "quando": lancamento.criado_em,
            "pontos": lancamento.pontos,
            "origem": lancamento.origem.value,
            "objetivo": nome,
            "descricao": lancamento.descricao,
        }
        for lancamento, nome in r
    ]


async def objetivos_do_dia(
    sessao: AsyncSession, *, usuario_id: UUID, hoje: date | None = None
) -> dict:
    """Meta do dia: quanto foi planejado e quanto já foi feito."""
    hoje = hoje or date.today()
    r = await sessao.execute(
        select(
            func.coalesce(func.sum(Ocorrencia.meta), 0),
            func.coalesce(func.sum(Ocorrencia.realizado), 0),
        )
        .join(Objetivo, Objetivo.id == Ocorrencia.objetivo_id)
        .where(
            Ocorrencia.titular_id == usuario_id,
            Ocorrencia.prevista_para == hoje,
            Objetivo.status != StatusObjetivo.ARQUIVADO,
        )
    )
    meta, feito = r.one()
    meta, feito = int(meta or 0), int(feito or 0)
    return {
        "meta": meta,
        "realizado": min(feito, meta) if meta else feito,
        "percentual": min(100, round(feito / meta * 100)) if meta else 0,
    }
