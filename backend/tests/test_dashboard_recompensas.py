"""Testes dos painéis e das trilhas de recompensa."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.exceptions import JaExiste, SemPermissao
from app.models.enums import (
    EscopoTrilha,
    Frequencia,
    OrigemPontos,
    PapelFamiliar,
    StatusRecompensa,
    TipoObjetivo,
)
from app.models.objetivos import Materia, Objetivo
from app.repositories import usuarios as repo
from app.services import agenda, auth, dashboard, ocorrencias
from app.services import pontos as servico_pontos
from app.services import recompensas as servico_rec

HOJE = date(2026, 8, 19)


def em(dia: date, hora: int = 10) -> datetime:
    return datetime.combine(dia, datetime.min.time(), tzinfo=UTC).replace(hour=hora)


async def _familia(sessao):
    return await auth.cadastrar_responsavel(
        sessao, nome_exibicao="Ricardo", username="ricardo",
        email="r@exemplo.com", senha="senha1234", nome_familia="Santos",
    )


async def _objetivo(sessao, aberta, nome="Curso de Inglês", materia_id=None, **kw):
    o = Objetivo(
        familia_id=aberta.familia_id, titular_id=kw.pop("titular_id", aberta.usuario.id),
        criador_id=aberta.usuario.id, tipo=TipoObjetivo.ESTUDO, nome=nome,
        meta_periodo=40, frequencia=Frequencia.DIARIA, materia_id=materia_id, **kw,
    )
    sessao.add(o)
    await sessao.flush()
    return o


async def _pontuar(sessao, aberta, objetivo, dia, pontos, chave=None):
    return await servico_pontos.creditar(
        sessao,
        beneficiario_id=aberta.usuario.id, familia_id=aberta.familia_id,
        objetivo=objetivo, pontos=pontos, origem=OrigemPontos.SESSAO_ESTUDO,
        chave_idempotencia=chave or f"teste:{objetivo.id}:{dia}",
        agora=em(dia),
    )


# ---------- sequência de dias ----------

async def test_sequencia_conta_dias_seguidos(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    for i in range(4):
        await _pontuar(sessao, a, o, HOJE - timedelta(days=i), 40)

    assert await dashboard.sequencia_de_dias(sessao, usuario_id=a.usuario.id, hoje=HOJE) == 4


async def test_buraco_quebra_a_sequencia(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    for i in (0, 1, 3, 4):          # faltou o dia 2
        await _pontuar(sessao, a, o, HOJE - timedelta(days=i), 40)

    assert await dashboard.sequencia_de_dias(sessao, usuario_id=a.usuario.id, hoje=HOJE) == 2


async def test_hoje_sem_pontos_ainda_nao_quebra(sessao):
    """O dia não acabou: quebrar agora puniria quem estuda à noite."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    for i in (1, 2, 3):
        await _pontuar(sessao, a, o, HOJE - timedelta(days=i), 40)

    assert await dashboard.sequencia_de_dias(sessao, usuario_id=a.usuario.id, hoje=HOJE) == 3


async def test_sem_pontos_a_sequencia_e_zero(sessao):
    a = await _familia(sessao)
    assert await dashboard.sequencia_de_dias(sessao, usuario_id=a.usuario.id, hoje=HOJE) == 0


async def test_adiantar_nao_conta_dia_futuro_na_sequencia(sessao):
    """Exigência da seção 9: estudar hoje não marca amanhã como estudado."""
    a = await _familia(sessao)
    o = await _objetivo(sessao, a, permite_adiantar=True, max_adiantamentos=1)
    ocs = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE + timedelta(days=2), hoje=HOJE)

    for oc in ocs[:2]:
        await ocorrencias.concluir(
            sessao, ocorrencia=oc, objetivo=o, familia_id=a.familia_id,
            papel=PapelFamiliar.ADMIN, minutos_validos=40, hoje=HOJE, agora=em(HOJE),
        )
    # dois créditos, ambos hoje → sequência de 1 dia, não de 2
    assert await dashboard.sequencia_de_dias(sessao, usuario_id=a.usuario.id, hoje=HOJE) == 1


# ---------- pontos por matéria ----------

async def test_pontos_separados_por_materia(sessao):
    a = await _familia(sessao)
    ingles = Materia(familia_id=a.familia_id, nome="Idioma")
    faculdade = Materia(familia_id=a.familia_id, nome="Faculdade")
    sessao.add_all([ingles, faculdade])
    await sessao.flush()

    o1 = await _objetivo(sessao, a, nome="Inglês", materia_id=ingles.id)
    o2 = await _objetivo(sessao, a, nome="Cálculo", materia_id=faculdade.id)
    await _pontuar(sessao, a, o1, HOJE, 40, chave="a")
    await _pontuar(sessao, a, o2, HOJE, 25, chave="b")

    por_materia = await dashboard.pontos_por_materia(sessao, usuario_id=a.usuario.id)
    assert por_materia == {"Idioma": 40, "Faculdade": 25}


# ---------- resumo ----------

async def test_resumo_junta_as_metricas(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)
    await _pontuar(sessao, a, o, HOJE, 40)

    usuario = await repo.por_id(sessao, a.usuario.id)
    r = await dashboard.resumo_pessoal(sessao, usuario=usuario, hoje=HOJE)
    assert r.pontos_totais == 40
    assert r.sequencia_dias == 1
    assert r.pendentes_hoje == 1
    assert r.estado_sessao is None


async def test_resumo_da_familia_lista_so_dependentes(sessao):
    a = await _familia(sessao)
    await auth.criar_dependente(
        sessao, responsavel=a.usuario, familia_id=a.familia_id,
        nome_exibicao="Pedro", username="pedro", email=None, senha_temporaria="temporaria1",
    )
    cartoes = await dashboard.resumo_da_familia(sessao, familia_id=a.familia_id, hoje=HOJE)
    assert [c.nome for c in cartoes] == ["Pedro"]


async def test_meta_do_dia(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    [oc] = await agenda.gerar_para_objetivo(sessao, o, ate=HOJE, hoje=HOJE)
    await ocorrencias.registrar_progresso(sessao, oc, 10)

    meta = await dashboard.objetivos_do_dia(sessao, usuario_id=a.usuario.id, hoje=HOJE)
    assert meta == {"meta": 40, "realizado": 10, "percentual": 25}


async def test_historico_pagina(sessao):
    a = await _familia(sessao)
    o = await _objetivo(sessao, a)
    for i in range(15):
        await _pontuar(sessao, a, o, HOJE - timedelta(days=i), 10, chave=f"h{i}")

    primeira = await dashboard.historico(sessao, usuario_id=a.usuario.id, limite=10)
    segunda = await dashboard.historico(
        sessao, usuario_id=a.usuario.id, limite=10, deslocamento=10
    )
    assert len(primeira) == 10
    assert len(segunda) == 5
    assert {x["id"] for x in primeira}.isdisjoint({x["id"] for x in segunda})


# ---------- trilhas de recompensa ----------

async def _trilha_com_niveis(sessao, a, vinculo):
    trilha = await servico_rec.criar_trilha(
        sessao, vinculo=vinculo, beneficiario_id=a.usuario.id,
        nome="Inglês", escopo=EscopoTrilha.TODOS,
    )
    for pontos, premio in [(100, "Uma sobremesa"), (200, "Uma hora de videogame"),
                           (300, "Escolher um passeio")]:
        await servico_rec.adicionar_nivel(
            sessao, trilha=trilha, vinculo=vinculo,
            pontos_necessarios=pontos, premio=premio,
        )
    return trilha


async def test_niveis_sao_numerados_sozinhos(sessao):
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    trilha = await _trilha_com_niveis(sessao, a, v)

    from sqlalchemy import select

    from app.models.pontos import NivelRecompensa
    r = await sessao.execute(
        select(NivelRecompensa.numero).where(NivelRecompensa.trilha_id == trilha.id)
        .order_by(NivelRecompensa.numero)
    )
    assert [n for (n,) in r] == [1, 2, 3]


async def test_nivel_precisa_exigir_mais_que_o_anterior(sessao):
    """Escada decrescente desbloquearia fora de ordem."""
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    trilha = await _trilha_com_niveis(sessao, a, v)
    with pytest.raises(JaExiste, match="exige 300 pontos"):
        await servico_rec.adicionar_nivel(
            sessao, trilha=trilha, vinculo=v, pontos_necessarios=150, premio="Fora de ordem"
        )


async def test_desbloqueia_ao_alcancar_e_nao_desconta(sessao):
    """O total é acumulativo: o nível seguinte continua alcançável."""
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    trilha = await _trilha_com_niveis(sessao, a, v)
    o = await _objetivo(sessao, a)
    await _pontuar(sessao, a, o, HOJE, 120)

    p = await servico_rec.avaliar(sessao, trilha=trilha)
    assert p.pontos == 120
    assert p.nivel_atual.numero == 1
    assert p.proximo_nivel.numero == 2
    assert p.faltam == 80
    assert len(p.desbloqueados) == 1


async def test_avaliar_duas_vezes_nao_duplica_desbloqueio(sessao):
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    trilha = await _trilha_com_niveis(sessao, a, v)
    o = await _objetivo(sessao, a)
    await _pontuar(sessao, a, o, HOJE, 250)

    await servico_rec.avaliar(sessao, trilha=trilha)
    p = await servico_rec.avaliar(sessao, trilha=trilha)

    from sqlalchemy import func, select

    from app.models.pontos import DesbloqueioRecompensa
    r = await sessao.execute(
        select(func.count()).select_from(DesbloqueioRecompensa)
        .where(DesbloqueioRecompensa.beneficiario_id == a.usuario.id)
    )
    assert int(r.scalar_one()) == 2       # níveis 1 e 2, uma vez cada
    assert len(p.desbloqueados) == 2


async def test_trilha_por_materia_soma_so_aquela_materia(sessao):
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    idioma = Materia(familia_id=a.familia_id, nome="Idioma")
    sessao.add(idioma)
    await sessao.flush()

    o1 = await _objetivo(sessao, a, nome="Inglês", materia_id=idioma.id)
    o2 = await _objetivo(sessao, a, nome="Cálculo")
    await _pontuar(sessao, a, o1, HOJE, 80, chave="x")
    await _pontuar(sessao, a, o2, HOJE, 500, chave="y")

    trilha = await servico_rec.criar_trilha(
        sessao, vinculo=v, beneficiario_id=a.usuario.id, nome="Só inglês",
        escopo=EscopoTrilha.MATERIA, filtro={"materia_id": str(idioma.id)},
    )
    assert await servico_rec.pontos_da_trilha(sessao, trilha) == 80


async def test_dependente_nao_cria_trilha(sessao):
    """Configurar a própria recompensa seria configurar o próprio prêmio."""
    a = await _familia(sessao)
    dep = await auth.criar_dependente(
        sessao, responsavel=a.usuario, familia_id=a.familia_id,
        nome_exibicao="Pedro", username="pedro", email=None, senha_temporaria="temporaria1",
    )
    v_dep = await repo.vinculo_ativo(sessao, dep.id)
    with pytest.raises(SemPermissao):
        await servico_rec.criar_trilha(
            sessao, vinculo=v_dep, beneficiario_id=dep.id,
            nome="Minha trilha", escopo=EscopoTrilha.TODOS,
        )


async def test_fluxo_solicitar_e_confirmar_entrega(sessao):
    a = await _familia(sessao)
    v = await repo.vinculo_ativo(sessao, a.usuario.id)
    trilha = await _trilha_com_niveis(sessao, a, v)
    o = await _objetivo(sessao, a)
    await _pontuar(sessao, a, o, HOJE, 120)
    await servico_rec.avaliar(sessao, trilha=trilha)

    from sqlalchemy import select

    from app.models.pontos import DesbloqueioRecompensa
    r = await sessao.execute(
        select(DesbloqueioRecompensa).where(
            DesbloqueioRecompensa.beneficiario_id == a.usuario.id
        )
    )
    d = r.scalars().first()

    pedido = await servico_rec.solicitar(
        sessao, desbloqueio_id=d.id, usuario_id=a.usuario.id
    )
    assert pedido.status == StatusRecompensa.SOLICITADA

    entregue = await servico_rec.confirmar_entrega(sessao, desbloqueio_id=d.id, vinculo=v)
    assert entregue.status == StatusRecompensa.ENTREGUE
    assert entregue.confirmado_por_id == a.usuario.id
