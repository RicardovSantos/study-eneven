"""Testes das sessões de estudo.

A pergunta que estes testes respondem: dá para inflar o tempo estudado?
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.exceptions import SemPermissao
from app.models.enums import (
    EstadoSessao,
    Frequencia,
    PapelFamiliar,
    StatusOcorrencia,
    TipoObjetivo,
    TipoSessao,
)
from app.models.objetivos import Objetivo
from app.services import agenda, auth, sessoes
from app.services import pontos as servico_pontos

HOJE = date(2026, 8, 19)
T0 = datetime(2026, 8, 19, 10, 0, 0, tzinfo=UTC)


def em(segundos: int) -> datetime:
    return T0 + timedelta(seconds=segundos)


async def _cenario(sessao, **kw_objetivo):
    aberta = await auth.cadastrar_responsavel(
        sessao, nome_exibicao="Ricardo", username="ricardo",
        email="r@exemplo.com", senha="senha1234", nome_familia="Santos",
    )
    padrao = dict(
        familia_id=aberta.familia_id, titular_id=aberta.usuario.id,
        criador_id=aberta.usuario.id, tipo=TipoObjetivo.ESTUDO,
        nome="Curso de Inglês", meta_periodo=40, frequencia=Frequencia.DIARIA,
    )
    padrao.update(kw_objetivo)
    objetivo = Objetivo(**padrao)
    sessao.add(objetivo)
    await sessao.flush()
    [ocorrencia] = await agenda.gerar_para_objetivo(sessao, objetivo, ate=HOJE, hoje=HOJE)
    return aberta, objetivo, ocorrencia


async def _abrir(sessao, aberta, objetivo, ocorrencia, **kw):
    return await sessoes.abrir(
        sessao, objetivo=objetivo, ocorrencia=ocorrencia,
        usuario_id=aberta.usuario.id, familia_id=aberta.familia_id,
        papel=PapelFamiliar.ADMIN, agora=T0, **kw,
    )


# ---------- abertura ----------

async def test_abrir_sessao_registra_evento(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    assert se.estado == EstadoSessao.ATIVA
    assert se.tipo == TipoSessao.NORMAL

    from sqlalchemy import select

    from app.models.sessoes import EventoSessao
    r = await sessao.execute(select(EventoSessao).where(EventoSessao.sessao_id == se.id))
    assert [e.tipo for e in r.scalars()] == ["session.started"]


async def test_nao_abre_duas_sessoes_ao_mesmo_tempo(sessao):
    """Duas rodando contariam o mesmo minuto duas vezes."""
    a, o, oc = await _cenario(sessao)
    await _abrir(sessao, a, o, oc)
    with pytest.raises(SemPermissao, match="já tem uma sessão aberta"):
        await _abrir(sessao, a, o, oc)


async def test_objetivo_que_exige_verificacao_recusa_sessao_normal(sessao):
    a, o, oc = await _cenario(sessao, exige_sessao_verificada=True)
    with pytest.raises(SemPermissao, match="aplicativo Android"):
        await _abrir(sessao, a, o, oc, verificada=False)


async def test_sessao_verificada_copia_a_configuracao_do_momento(sessao):
    """Mudar o intervalo depois não pode reescrever o histórico."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=True)
    assert se.exige_captura is True
    assert se.intervalo_captura_seg == 480      # os 8 minutos da especificação


# ---------- contagem de tempo ----------

async def test_heartbeat_credita_o_intervalo(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)

    r = await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(30))
    assert r.segundos_creditados == 30
    assert se.segundos_validos == 30
    assert se.segundos_brutos == 30


async def test_heartbeats_seguidos_somam(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    for s in (30, 60, 90):
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(s))
    assert se.segundos_validos == 90


async def test_lacuna_grande_nao_vira_tempo_valido(sessao):
    """O ponto central: silêncio não é estudo.

    O aparelho sumiu por 20 minutos. O relógio de parede andou, mas não há
    como afirmar que a pessoa estudou — creditar seria inventar dado.
    """
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)

    r = await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(1200))
    assert r.houve_lacuna is True
    assert r.segundos_creditados == 0
    assert se.segundos_validos == 0
    assert se.segundos_brutos == 1200
    assert se.estado == EstadoSessao.INTERROMPIDA


async def test_interrupcao_vira_evento_para_o_responsavel(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(1200))

    from sqlalchemy import select

    from app.models.sessoes import EventoSessao
    r = await sessao.execute(select(EventoSessao).where(EventoSessao.sessao_id == se.id))
    assert "session.monitoring_interrupted" in [e.tipo for e in r.scalars()]


async def test_sessao_volta_a_contar_depois_da_lacuna(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(1200))
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(1230))

    assert se.estado == EstadoSessao.ATIVA
    assert se.segundos_validos == 30       # só o intervalo depois da volta


async def test_pausa_nao_conta_como_estudo(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)

    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(60))
    await sessoes.pausar(sessao, sessao_estudo=se, agora=em(60))
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(90))
    await sessoes.retomar(sessao, sessao_estudo=se, agora=em(120))
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(150))

    assert se.segundos_validos == 90       # 60 antes + 30 depois; a pausa não


async def test_retomar_nao_credita_o_tempo_parado(sessao):
    """Pausar às 10h, voltar às 12h: as 2 horas não viram estudo."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    await sessoes.pausar(sessao, sessao_estudo=se, agora=em(10))
    await sessoes.retomar(sessao, sessao_estudo=se, agora=em(7200))
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(7230))
    assert se.segundos_validos == 40       # 10 antes da pausa + 30 depois


# ---------- verificado x não verificado ----------

async def test_verificado_so_com_captura_funcionando(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=True)

    await sessoes.heartbeat(
        sessao, sessao_estudo=se, agora=em(30), capturando=True, localizando=True
    )
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(60), capturando=False)

    assert se.segundos_verificados == 30
    assert se.segundos_nao_verificados == 30
    assert se.segundos_validos == 60


async def test_sessao_normal_nunca_gera_tempo_verificado(sessao):
    """A web não consegue monitorar outros apps; não pode fingir que sim."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=False)
    await sessoes.heartbeat(
        sessao, sessao_estudo=se, agora=em(60), capturando=True, localizando=True
    )
    assert se.segundos_verificados == 0
    assert se.segundos_nao_verificados == 60


async def test_interrompida_nao_fica_totalmente_verificada(sessao):
    """Exigência explícita da seção 15.6."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=True)
    await sessoes.heartbeat(
        sessao, sessao_estudo=se, agora=em(60), capturando=True, localizando=True
    )
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(1300))   # sumiu

    assert se.segundos_verificados < se.segundos_brutos
    assert se.estado == EstadoSessao.INTERROMPIDA


# ---------- encerramento ----------

async def test_finalizar_credita_o_tempo_na_ocorrencia(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    for s in range(30, 1230, 30):          # 20 minutos de heartbeats
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(s))

    r = await sessoes.finalizar(
        sessao, sessao_estudo=se, papel=PapelFamiliar.ADMIN, agora=em(1200)
    )
    assert r.minutos_validos == 20
    assert oc.realizado == 20
    assert r.ocorrencia_concluida is False       # a meta é 40


async def test_bater_a_meta_conclui_e_pontua(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    for s in range(30, 2430, 30):          # 40 minutos
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(s))

    r = await sessoes.finalizar(
        sessao, sessao_estudo=se, papel=PapelFamiliar.ADMIN, agora=em(2400)
    )
    assert r.ocorrencia_concluida is True
    assert r.pontos_creditados == 40
    assert oc.status == StatusOcorrencia.CONCLUIDA
    assert await servico_pontos.total_de(sessao, beneficiario_id=a.usuario.id) == 40


async def test_finalizar_duas_vezes_nao_credita_em_dobro(sessao):
    """O Android reenvia o encerramento quando perde a resposta."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    for s in range(30, 2430, 30):
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(s))

    await sessoes.finalizar(
        sessao, sessao_estudo=se, papel=PapelFamiliar.ADMIN,
        chave_finalizacao="abc123", agora=em(2400),
    )
    await sessoes.finalizar(
        sessao, sessao_estudo=se, papel=PapelFamiliar.ADMIN,
        chave_finalizacao="abc123", agora=em(2500),
    )
    assert await servico_pontos.total_de(sessao, beneficiario_id=a.usuario.id) == 40
    assert oc.realizado == 40


async def test_dependente_com_sessao_normal_nao_pontua(sessao):
    """Sem captura funcionando, não há tempo verificado — e sem tempo
    verificado, dependente não pontua (seção 10.1)."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=False)
    for s in range(30, 2430, 30):
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(s))

    r = await sessoes.finalizar(
        sessao, sessao_estudo=se, papel=PapelFamiliar.DEPENDENTE, agora=em(2400)
    )
    assert r.ocorrencia_concluida is True
    assert r.pontos_creditados == 0


async def test_heartbeat_em_sessao_encerrada_e_recusado(sessao):
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    await sessoes.finalizar(sessao, sessao_estudo=se, papel=PapelFamiliar.ADMIN, agora=em(60))
    with pytest.raises(SemPermissao, match="já foi encerrada"):
        await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(90))


# ---------- varredura ----------

async def test_varredura_marca_quem_parou_de_dar_noticia(sessao):
    """O painel do responsável precisa mostrar a interrupção mesmo com o
    aparelho calado — o heartbeat só detecta quando ele volta."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc)
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(30))

    nenhuma = await sessoes.varrer_interrompidas(sessao, agora=em(60))
    assert nenhuma == []

    achadas = await sessoes.varrer_interrompidas(sessao, agora=em(300))
    assert [x.id for x in achadas] == [se.id]
    assert se.estado == EstadoSessao.INTERROMPIDA


async def test_soma_das_contagens_nunca_passa_do_bruto(sessao):
    """A restrição CHECK do banco garante isso; o serviço não pode violá-la."""
    a, o, oc = await _cenario(sessao)
    se = await _abrir(sessao, a, o, oc, verificada=True)
    for s in range(30, 600, 30):
        await sessoes.heartbeat(
            sessao, sessao_estudo=se, agora=em(s), capturando=(s % 60 == 0), localizando=True
        )
    await sessoes.heartbeat(sessao, sessao_estudo=se, agora=em(2000))    # lacuna

    assert se.segundos_validos <= se.segundos_brutos
    assert se.segundos_verificados + se.segundos_nao_verificados <= se.segundos_brutos
