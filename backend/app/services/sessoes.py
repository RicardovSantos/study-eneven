"""Sessões de estudo com o tempo apurado pelo servidor.

O relógio do cliente não define nada. O aparelho apenas avisa que
continua vivo (heartbeat); quem mede o tempo é o servidor, pela diferença
entre dois avisos. É isso que impede alguém de mandar "estudei 8 horas"
de um `curl`.

**A regra que sustenta a confiança:** um intervalo maior que o tempo
limite não vira tempo válido. Se o aparelho ficou 20 minutos sem dar
notícia, esses 20 minutos entram no tempo bruto (o relógio de parede
andou) mas não no tempo válido — não há como afirmar que a pessoa estava
estudando. Marcar como estudado seria inventar um dado.

As quatro contagens da tabela existem justamente para não misturar essas
coisas: bruto (parede), válido (contou como estudo), verificado (com
captura funcionando) e não verificado (o resto).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NaoEncontrado, SemPermissao
from app.models.enums import (
    EstadoSessao,
    PapelFamiliar,
    StatusOcorrencia,
    TipoSessao,
)
from app.models.objetivos import Objetivo, Ocorrencia
from app.models.sessoes import EventoSessao, SessaoEstudo
from app.services import ocorrencias as servico_oc

ORIGEM_SERVIDOR = "servidor"


@dataclass
class ResultadoHeartbeat:
    sessao: SessaoEstudo
    segundos_creditados: int
    houve_lacuna: bool
    lacuna_segundos: int


async def _proxima_sequencia(sessao: AsyncSession, sessao_id: UUID) -> int:
    r = await sessao.execute(
        select(func.coalesce(func.max(EventoSessao.sequencia), 0)).where(
            EventoSessao.sessao_id == sessao_id
        )
    )
    return int(r.scalar_one() or 0) + 1


async def registrar_evento(
    sessao: AsyncSession,
    sessao_estudo: SessaoEstudo,
    tipo: str,
    dados: dict | None = None,
    origem: str = ORIGEM_SERVIDOR,
    agora: datetime | None = None,
) -> EventoSessao:
    """Trilha imutável do que aconteceu. Só insere, nunca atualiza."""
    evento = EventoSessao(
        sessao_id=sessao_estudo.id,
        tipo=tipo,
        ocorrido_em=agora or datetime.now(UTC),
        dados=dados,
        origem=origem,
        sequencia=await _proxima_sequencia(sessao, sessao_estudo.id),
    )
    sessao.add(evento)
    await sessao.flush()
    return evento


def _com_fuso(momento: datetime | None) -> datetime | None:
    """SQLite devolve datetime sem fuso; o PostgreSQL devolve com."""
    if momento is None:
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=UTC)


async def abrir(
    sessao: AsyncSession,
    *,
    objetivo: Objetivo,
    ocorrencia: Ocorrencia | None,
    usuario_id: UUID,
    familia_id: UUID,
    papel: PapelFamiliar | None,
    dispositivo_id: UUID | None = None,
    verificada: bool = False,
    agora: datetime | None = None,
) -> SessaoEstudo:
    """Abre uma sessão. Recusa se já houver outra em andamento.

    Uma sessão por vez, por usuário: duas rodando ao mesmo tempo
    contariam o mesmo minuto duas vezes.
    """
    s = get_settings()
    agora = agora or datetime.now(UTC)

    aberta = await sessao.execute(
        select(SessaoEstudo).where(
            SessaoEstudo.usuario_id == usuario_id,
            SessaoEstudo.estado.in_([EstadoSessao.ATIVA, EstadoSessao.PAUSADA]),
        )
    )
    if aberta.scalars().first() is not None:
        raise SemPermissao("Você já tem uma sessão aberta. Encerre-a antes de começar outra.")

    if objetivo.exige_sessao_verificada and not verificada:
        raise SemPermissao(
            "Este objetivo exige sessão verificada, disponível no aplicativo Android."
        )

    sessao_estudo = SessaoEstudo(
        ocorrencia_id=ocorrencia.id if ocorrencia else None,
        objetivo_id=objetivo.id,
        usuario_id=usuario_id,
        familia_id=familia_id,
        dispositivo_id=dispositivo_id,
        tipo=TipoSessao.VERIFICADA if verificada else TipoSessao.NORMAL,
        estado=EstadoSessao.ATIVA,
        iniciada_em=agora,
        ultimo_heartbeat_em=agora,
        # Cópia da configuração vigente: se o responsável mudar o
        # intervalo depois, o histórico continua contando como esta
        # sessão realmente foi feita.
        exige_captura=verificada,
        exige_localizacao=verificada and s.LOCATION_WITH_CAPTURE,
        intervalo_captura_seg=s.CAPTURE_INTERVAL_SECONDS if verificada else None,
    )
    sessao.add(sessao_estudo)
    await sessao.flush()
    await registrar_evento(
        sessao, sessao_estudo, "session.started",
        {"tipo": sessao_estudo.tipo.value}, agora=agora,
    )
    return sessao_estudo


async def heartbeat(
    sessao: AsyncSession,
    *,
    sessao_estudo: SessaoEstudo,
    agora: datetime | None = None,
    capturando: bool = False,
    localizando: bool = False,
) -> ResultadoHeartbeat:
    """Contabiliza o tempo desde o último aviso.

    O crédito acontece aqui, e não no fim: uma sessão que morre com o
    aparelho não perde o que já foi estudado.
    """
    s = get_settings()
    agora = agora or datetime.now(UTC)

    if sessao_estudo.estado == EstadoSessao.FINALIZADA:
        raise SemPermissao("Esta sessão já foi encerrada.")

    referencia = _com_fuso(sessao_estudo.ultimo_heartbeat_em) or _com_fuso(
        sessao_estudo.iniciada_em
    )
    decorrido = max(0, int((agora - referencia).total_seconds()))
    limite = s.SESSION_HEARTBEAT_TIMEOUT_SECONDS

    houve_lacuna = decorrido > limite
    creditado = 0

    # O relógio de parede sempre anda, tenha havido lacuna ou não.
    sessao_estudo.segundos_brutos += decorrido

    if houve_lacuna:
        # Ninguém sabe o que aconteceu nesse intervalo: não vira tempo
        # válido. Fica registrado como evento para o responsável ver.
        sessao_estudo.estado = EstadoSessao.INTERROMPIDA
        sessao_estudo.motivo_interrupcao = "sem heartbeat"
        await registrar_evento(
            sessao, sessao_estudo, "session.monitoring_interrupted",
            {"lacuna_segundos": decorrido, "limite": limite}, agora=agora,
        )
    elif sessao_estudo.estado == EstadoSessao.PAUSADA:
        # Pausa não conta como estudo (seção 10.1).
        pass
    else:
        creditado = decorrido
        sessao_estudo.segundos_validos += creditado
        verificado_agora = (
            sessao_estudo.tipo == TipoSessao.VERIFICADA
            and capturando
            and (localizando or not sessao_estudo.exige_localizacao)
        )
        if verificado_agora:
            sessao_estudo.segundos_verificados += creditado
        else:
            sessao_estudo.segundos_nao_verificados += creditado
        sessao_estudo.estado = EstadoSessao.ATIVA

    sessao_estudo.ultimo_heartbeat_em = agora
    await sessao.flush()
    return ResultadoHeartbeat(
        sessao_estudo, creditado, houve_lacuna, decorrido if houve_lacuna else 0
    )


async def pausar(
    sessao: AsyncSession, *, sessao_estudo: SessaoEstudo, agora: datetime | None = None
) -> SessaoEstudo:
    """Fecha o tempo corrente antes de pausar, para nada se perder."""
    agora = agora or datetime.now(UTC)
    if sessao_estudo.estado == EstadoSessao.FINALIZADA:
        raise SemPermissao("Esta sessão já foi encerrada.")

    if sessao_estudo.estado == EstadoSessao.ATIVA:
        await heartbeat(sessao, sessao_estudo=sessao_estudo, agora=agora)

    sessao_estudo.estado = EstadoSessao.PAUSADA
    sessao_estudo.pausada_em = agora
    await registrar_evento(sessao, sessao_estudo, "session.paused", agora=agora)
    await sessao.flush()
    return sessao_estudo


async def retomar(
    sessao: AsyncSession, *, sessao_estudo: SessaoEstudo, agora: datetime | None = None
) -> SessaoEstudo:
    agora = agora or datetime.now(UTC)
    if sessao_estudo.estado == EstadoSessao.FINALIZADA:
        raise SemPermissao("Esta sessão já foi encerrada.")

    sessao_estudo.estado = EstadoSessao.ATIVA
    sessao_estudo.retomada_em = agora
    # Zera a referência: o tempo parado não pode ser creditado ao voltar.
    sessao_estudo.ultimo_heartbeat_em = agora
    await registrar_evento(sessao, sessao_estudo, "session.resumed", agora=agora)
    await sessao.flush()
    return sessao_estudo


@dataclass
class ResultadoFinal:
    sessao: SessaoEstudo
    minutos_validos: int
    minutos_verificados: int
    ocorrencia_concluida: bool
    pontos_creditados: int


async def finalizar(
    sessao: AsyncSession,
    *,
    sessao_estudo: SessaoEstudo,
    papel: PapelFamiliar | None,
    resumo: str | None = None,
    chave_finalizacao: str | None = None,
    agora: datetime | None = None,
) -> ResultadoFinal:
    """Encerra, credita o tempo na ocorrência e conclui se bateu a meta.

    `chave_finalizacao` é única no banco: o Android pode reenviar o
    encerramento depois de perder a resposta, e o reenvio não credita
    duas vezes.
    """
    agora = agora or datetime.now(UTC)

    if sessao_estudo.estado == EstadoSessao.FINALIZADA:
        return ResultadoFinal(
            sessao_estudo,
            sessao_estudo.segundos_validos // 60,
            sessao_estudo.segundos_verificados // 60,
            False,
            0,
        )

    if sessao_estudo.estado == EstadoSessao.ATIVA:
        await heartbeat(sessao, sessao_estudo=sessao_estudo, agora=agora)

    sessao_estudo.estado = EstadoSessao.FINALIZADA
    sessao_estudo.finalizada_em = agora
    sessao_estudo.resumo_final = resumo
    if chave_finalizacao:
        sessao_estudo.chave_finalizacao = chave_finalizacao

    minutos_validos = sessao_estudo.segundos_validos // 60
    minutos_verificados = sessao_estudo.segundos_verificados // 60

    await registrar_evento(
        sessao, sessao_estudo, "session.completed",
        {
            "segundos_validos": sessao_estudo.segundos_validos,
            "segundos_verificados": sessao_estudo.segundos_verificados,
        },
        agora=agora,
    )

    concluida, pontos = False, 0
    if sessao_estudo.ocorrencia_id and minutos_validos > 0:
        ocorrencia = await sessao.get(Ocorrencia, sessao_estudo.ocorrencia_id)
        objetivo = await sessao.get(Objetivo, sessao_estudo.objetivo_id)
        if ocorrencia is not None and objetivo is not None:
            await servico_oc.registrar_progresso(sessao, ocorrencia, minutos_validos)

            if (
                ocorrencia.status == StatusOcorrencia.PENDENTE
                and ocorrencia.realizado >= ocorrencia.meta
            ):
                resultado = await servico_oc.concluir(
                    sessao,
                    ocorrencia=ocorrencia,
                    objetivo=objetivo,
                    familia_id=sessao_estudo.familia_id,
                    papel=papel,
                    minutos_validos=minutos_validos,
                    minutos_verificados=minutos_verificados,
                    sessao_estudo_id=sessao_estudo.id,
                    hoje=agora.date(),
                    agora=agora,
                )
                concluida = True
                pontos = resultado.pontos_creditados

    await sessao.flush()
    return ResultadoFinal(
        sessao_estudo, minutos_validos, minutos_verificados, concluida, pontos
    )


async def sessao_aberta_de(
    sessao: AsyncSession, usuario_id: UUID
) -> SessaoEstudo | None:
    r = await sessao.execute(
        select(SessaoEstudo).where(
            SessaoEstudo.usuario_id == usuario_id,
            SessaoEstudo.estado.in_(
                [EstadoSessao.ATIVA, EstadoSessao.PAUSADA, EstadoSessao.INTERROMPIDA]
            ),
        )
    )
    return r.scalars().first()


async def obter(
    sessao: AsyncSession, *, sessao_id: UUID, usuario_id: UUID, familia_id: UUID,
    papel: PapelFamiliar | None,
) -> SessaoEstudo:
    """Dono vê a própria; responsável vê as da família."""
    s = await sessao.get(SessaoEstudo, sessao_id)
    if s is None or s.familia_id != familia_id:
        raise NaoEncontrado("Sessão não encontrada.")
    if papel != PapelFamiliar.ADMIN and s.usuario_id != usuario_id:
        raise NaoEncontrado("Sessão não encontrada.")
    return s


async def varrer_interrompidas(
    sessao: AsyncSession, *, familia_id: UUID | None = None, agora: datetime | None = None
) -> list[SessaoEstudo]:
    """Marca como interrompida quem parou de dar notícia.

    O heartbeat só detecta a lacuna quando o aparelho volta. Esta
    varredura é o que faz o painel do responsável mostrar "sessão
    interrompida" enquanto o aparelho continua calado.
    """
    s = get_settings()
    agora = agora or datetime.now(UTC)

    consulta = select(SessaoEstudo).where(SessaoEstudo.estado == EstadoSessao.ATIVA)
    if familia_id is not None:
        consulta = consulta.where(SessaoEstudo.familia_id == familia_id)

    r = await sessao.execute(consulta)
    interrompidas = []
    for se in r.scalars():
        referencia = _com_fuso(se.ultimo_heartbeat_em) or _com_fuso(se.iniciada_em)
        if (agora - referencia).total_seconds() > s.SESSION_HEARTBEAT_TIMEOUT_SECONDS:
            se.estado = EstadoSessao.INTERROMPIDA
            se.motivo_interrupcao = "sem heartbeat"
            await registrar_evento(
                sessao, se, "session.monitoring_interrupted",
                {"detectado_por": "varredura"}, agora=agora,
            )
            interrompidas.append(se)
    await sessao.flush()
    return interrompidas
