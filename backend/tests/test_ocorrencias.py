"""Testes do motor de ocorrências, adiantamento e pontos.

É a parte que a versão em localStorage não conseguia fazer, então é
onde vale gastar mais teste.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.exceptions import SemPermissao
from app.models.enums import (
    Frequencia,
    MomentoConclusao,
    PapelFamiliar,
    StatusOcorrencia,
    TipoObjetivo,
)
from app.models.objetivos import Objetivo
from app.services import agenda, auth, ocorrencias
from app.services import pontos as servico_pontos

HOJE = date(2026, 8, 19)          # uma quarta-feira
AGORA = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)


async def _familia(sessao):
    aberta = await auth.cadastrar_responsavel(
        sessao, nome_exibicao="Ricardo", username="ricardo",
        email="r@exemplo.com", senha="senha1234", nome_familia="Santos",
    )
    return aberta


async def _objetivo(sessao, aberta, **kw):
    padrao = dict(
        familia_id=aberta.familia_id,
        titular_id=aberta.usuario.id,
        criador_id=aberta.usuario.id,
        tipo=TipoObjetivo.ESTUDO,
        nome="Curso de Inglês",
        meta_periodo=40,
        frequencia=Frequencia.DIARIA,
        permite_adiantar=True,
        max_adiantamentos=1,
    )
    padrao.update(kw)
    o = Objetivo(**padrao)
    sessao.add(o)
    await sessao.flush()
    return o


# ---------- geração da agenda ----------

async def test_gera_uma_ocorrencia_por_dia(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    novas = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=6), hoje=HOJE)
    assert len(novas) == 7
    assert novas[0].prevista_para == HOJE
    assert novas[0].meta == 40


async def test_respeita_os_dias_da_semana(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, dias_semana=[1, 3, 5])   # seg, qua, sex
    novas = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=6), hoje=HOJE)
    dias = {(x.prevista_para.weekday() + 1) % 7 for x in novas}
    assert dias == {1, 3, 5}


async def test_geracao_e_idempotente(sessao):
    """Rodar duas vezes não pode duplicar obrigação."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    primeira = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=3), hoje=HOJE)
    segunda = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=3), hoje=HOJE)
    assert len(primeira) == 4
    assert segunda == []


async def test_nao_gera_antes_do_inicio_nem_depois_do_prazo(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, inicia_em=HOJE + timedelta(days=2),
                        prazo_final=HOJE + timedelta(days=4))
    novas = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=10), hoje=HOJE)
    assert [x.prevista_para for x in novas] == [
        HOJE + timedelta(days=2), HOJE + timedelta(days=3), HOJE + timedelta(days=4)
    ]


async def test_semanal_gera_uma_por_semana(sessao):
    """De 19/08 a 08/09 são quatro semanas tocadas, não três.

    A primeira é parcial (começa na quarta, 19), então ancora no próprio
    dia 19 em vez do domingo 16 — senão o período corrente ficaria sem
    obrigação nenhuma. As seguintes ancoram no domingo.
    """
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, frequencia=Frequencia.SEMANAL, meta_periodo=300)
    novas = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=20), hoje=HOJE)
    assert [x.prevista_para for x in novas] == [
        date(2026, 8, 19),      # semana corrente, já em andamento
        date(2026, 8, 23),      # domingo
        date(2026, 8, 30),      # domingo
        date(2026, 9, 6),       # domingo
    ]


async def test_pendente_de_ontem_vira_perdida(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE - timedelta(days=3))
    quantas = await agenda.marcar_perdidas(sessao, a.usuario.id, hoje=HOJE)
    assert quantas == 3


# ---------- conclusão ----------

async def test_concluir_no_prazo_credita_um_ponto_por_minuto(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)

    r = await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    assert r.momento == MomentoConclusao.NO_PRAZO
    assert r.pontos_creditados == 40
    assert await servico_pontos.total_de(sessao, beneficiario_id=a.usuario.id) == 40


async def test_concluir_duas_vezes_nao_credita_em_dobro(sessao):
    """Idempotência: o reenvio da rede não pode inflar o placar."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)

    for _ in range(3):
        await ocorrencias.concluir(
            sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )
    assert await servico_pontos.total_de(sessao, beneficiario_id=a.usuario.id) == 40


async def test_atraso_e_registrado_como_atrasada(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(
        sessao, o, ate=HOJE - timedelta(days=2), hoje=HOJE - timedelta(days=2)
    )
    r = await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    assert r.momento == MomentoConclusao.ATRASADA


async def test_dependente_so_pontua_tempo_verificado(sessao):
    """Sessão sem captura funcionando não vira ponto para dependente."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)

    r = await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.DEPENDENTE,
        minutos_validos=40, minutos_verificados=10, hoje=HOJE, agora=AGORA,
    )
    assert r.pontos_creditados == 10


async def test_teto_diario_limita_o_credito(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, limite_pontos_dia=30)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)
    r = await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=120, hoje=HOJE, agora=AGORA,
    )
    assert r.pontos_creditados == 30


async def test_tarefa_usa_pontos_fixos(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, tipo=TipoObjetivo.TAREFA, pontos_fixos=8,
                        frequencia=Frequencia.MENSAL, meta_periodo=5)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)
    r = await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, hoje=HOJE, agora=AGORA,
    )
    assert r.pontos_creditados == 8


# ---------- adiantamento ----------

async def _agenda_de_dois_dias(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    ocs = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=3), hoje=HOJE)
    return a, o, ocs


async def test_adiantar_exige_concluir_a_de_hoje(sessao):
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    with pytest.raises(SemPermissao, match="Conclua a atividade de hoje"):
        await ocorrencias.concluir(
            sessao, ocorrencia=ocs[1], objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )


async def test_adiantar_a_proxima_depois_de_concluir_hoje(sessao):
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    await ocorrencias.concluir(
        sessao, ocorrencia=ocs[0], objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    r = await ocorrencias.concluir(
        sessao, ocorrencia=ocs[1], objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    assert r.momento == MomentoConclusao.ADIANTADA
    assert r.ocorrencia.dias_adiantados == 1
    # a data prevista NÃO muda: é ela que faz o painel de amanhã mostrar
    # "concluída antecipadamente" em vez de cobrar de novo
    assert r.ocorrencia.prevista_para == HOJE + timedelta(days=1)


async def test_adiantada_nao_reaparece_como_pendente(sessao):
    """O comportamento que a especificação exige explicitamente."""
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    for oc in ocs[:2]:
        await ocorrencias.concluir(
            sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )
    amanha = HOJE + timedelta(days=1)
    novas = await agenda.gerar_para_objetivo(sessao, o, ate=amanha, hoje=amanha)
    assert novas == []
    assert ocs[1].status == StatusOcorrencia.CONCLUIDA


async def test_limite_de_adiantamento_e_respeitado(sessao):
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    for oc in ocs[:2]:
        await ocorrencias.concluir(
            sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )
    with pytest.raises(SemPermissao, match="limite deste objetivo"):
        await ocorrencias.concluir(
            sessao, ocorrencia=ocs[2], objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )


async def test_nao_da_para_pular_a_fila(sessao):
    """Respeitar a ordem das aulas: não dá para pular a 12 e fazer a 13."""
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    await ocorrencias.concluir(
        sessao, ocorrencia=ocs[0], objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    with pytest.raises(SemPermissao, match="atividade anterior"):
        await ocorrencias.concluir(
            sessao, ocorrencia=ocs[2], objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )


async def test_objetivo_sem_adiantamento_nao_adianta(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, permite_adiantar=False)
    ocs = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=2), hoje=HOJE)
    await ocorrencias.concluir(
        sessao, ocorrencia=ocs[0], objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    with pytest.raises(SemPermissao, match="não está configurado"):
        await ocorrencias.concluir(
            sessao, ocorrencia=ocs[1], objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )


async def test_pontos_do_adiantamento_caem_no_dia_real(sessao):
    """Estudou hoje, conta hoje — não na data prevista da aula."""
    a, o, ocs = await _agenda_de_dois_dias(sessao)
    for oc in ocs[:2]:
        await ocorrencias.concluir(
            sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
        )
    de_hoje = await servico_pontos.creditados_hoje(
        sessao, beneficiario_id=a.usuario.id, objetivo_id=o.id, dia=HOJE
    )
    de_amanha = await servico_pontos.creditados_hoje(
        sessao, beneficiario_id=a.usuario.id, objetivo_id=o.id, dia=HOJE + timedelta(days=1)
    )
    assert de_hoje == 80
    assert de_amanha == 0


# ---------- desfazer ----------

async def test_desfazer_estorna_com_lancamento_negativo(sessao):
    """Os pontos não somem: entra a linha oposta, e o razão fica auditável."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)
    await ocorrencias.concluir(
        sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
        papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=AGORA,
    )
    await ocorrencias.desfazer(sessao, ocorrencia=oc, objetivo=o)

    assert await servico_pontos.total_de(sessao, beneficiario_id=a.usuario.id) == 0
    assert oc.status == StatusOcorrencia.PENDENTE

    from sqlalchemy import func, select

    from app.models.pontos import LancamentoPontos
    r = await sessao.execute(
        select(func.count()).select_from(LancamentoPontos)
        .where(LancamentoPontos.ocorrencia_id == oc.id)
    )
    assert int(r.scalar_one()) == 2       # o crédito e o estorno
