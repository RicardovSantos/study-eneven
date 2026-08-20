"""Testes HTTP dos painéis e recompensas."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_sessao
from app.main import app

RESPONSAVEL = {
    "nome_exibicao": "Ricardo Vieira dos Santos", "username": "ricardo",
    "email": "ricardo@exemplo.com", "senha": "senha1234", "nome_familia": "Santos",
}


@pytest_asyncio.fixture
async def cliente(sessao):
    async def _s():
        yield sessao

    app.dependency_overrides[get_sessao] = _s
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as c:
        yield c
    app.dependency_overrides.clear()


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _admin(cliente):
    r = await cliente.post("/api/v1/auth/cadastrar", json=RESPONSAVEL)
    return r.json()["access_token"]


async def _dependente(cliente, admin):
    await cliente.post(
        "/api/v1/auth/dependentes", headers=_auth(admin),
        json={"nome_exibicao": "Pedro", "username": "pedro",
              "senha_temporaria": "temporaria1"},
    )
    r = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    return r.json()["access_token"]


async def test_painel_pessoal_responde_vazio_sem_erro(cliente):
    """Conta nova é o caso mais comum de tela quebrada."""
    token = await _admin(cliente)
    r = await cliente.get("/api/v1/dashboard", headers=_auth(token))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["resumo"]["pontos_totais"] == 0
    assert corpo["resumo"]["sequencia_dias"] == 0
    assert corpo["meta_do_dia"]["percentual"] == 0
    assert len(corpo["serie_semana"]) == 7


async def test_painel_da_familia_e_so_do_responsavel(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)

    ok = await cliente.get("/api/v1/dashboard/familia", headers=_auth(admin))
    assert ok.status_code == 200
    assert [d["nome"] for d in ok.json()["dependentes"]] == ["Pedro"]

    proibido = await cliente.get("/api/v1/dashboard/familia", headers=_auth(dep))
    assert proibido.status_code == 403


async def test_dependente_nao_ve_historico_alheio(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)
    eu_admin = (await cliente.get("/api/v1/auth/eu", headers=_auth(admin))).json()

    r = await cliente.get(
        f"/api/v1/historico?titular_id={eu_admin['id']}", headers=_auth(dep)
    )
    assert r.status_code == 403


async def test_responsavel_ve_historico_do_dependente(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)
    eu_dep = (await cliente.get("/api/v1/auth/eu", headers=_auth(dep))).json()

    r = await cliente.get(
        f"/api/v1/historico?titular_id={eu_dep['id']}", headers=_auth(admin)
    )
    assert r.status_code == 200


async def test_criar_trilha_com_niveis_e_consultar(cliente):
    token = await _admin(cliente)
    t = await cliente.post(
        "/api/v1/recompensas/trilhas", headers=_auth(token),
        json={"nome": "Inglês", "escopo": "all"},
    )
    assert t.status_code == 201
    trilha_id = t.json()["trilha_id"]

    for pontos, premio in [(100, "Uma sobremesa"), (200, "Uma hora de videogame")]:
        n = await cliente.post(
            f"/api/v1/recompensas/trilhas/{trilha_id}/niveis", headers=_auth(token),
            json={"pontos_necessarios": pontos, "premio": premio},
        )
        assert n.status_code == 201

    lista = await cliente.get("/api/v1/recompensas", headers=_auth(token))
    assert lista.json()[0]["proximo_nivel"]["pontos_necessarios"] == 100
    assert lista.json()[0]["faltam"] == 100


async def test_nivel_decrescente_e_recusado(cliente):
    token = await _admin(cliente)
    t = await cliente.post(
        "/api/v1/recompensas/trilhas", headers=_auth(token),
        json={"nome": "Inglês", "escopo": "all"},
    )
    trilha_id = t.json()["trilha_id"]
    await cliente.post(
        f"/api/v1/recompensas/trilhas/{trilha_id}/niveis", headers=_auth(token),
        json={"pontos_necessarios": 200, "premio": "Prêmio"},
    )
    r = await cliente.post(
        f"/api/v1/recompensas/trilhas/{trilha_id}/niveis", headers=_auth(token),
        json={"pontos_necessarios": 100, "premio": "Fora de ordem"},
    )
    assert r.status_code == 409


async def test_dependente_nao_configura_a_propria_recompensa(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)
    r = await cliente.post(
        "/api/v1/recompensas/trilhas", headers=_auth(dep),
        json={"nome": "Minha trilha", "escopo": "all"},
    )
    assert r.status_code == 403


async def test_trilha_de_outra_familia_da_404(cliente):
    admin_a = await _admin(cliente)
    t = await cliente.post(
        "/api/v1/recompensas/trilhas", headers=_auth(admin_a),
        json={"nome": "Inglês", "escopo": "all"},
    )
    trilha_id = t.json()["trilha_id"]

    outra = await cliente.post(
        "/api/v1/auth/cadastrar",
        json={**RESPONSAVEL, "username": "outra", "email": "o@exemplo.com",
              "nome_familia": "Outra"},
    )
    r = await cliente.post(
        f"/api/v1/recompensas/trilhas/{trilha_id}/niveis",
        headers=_auth(outra.json()["access_token"]),
        json={"pontos_necessarios": 50, "premio": "Invasão"},
    )
    assert r.status_code == 404


async def test_rotas_de_painel_exigem_autenticacao(cliente):
    for caminho in ["/api/v1/dashboard", "/api/v1/dashboard/familia",
                    "/api/v1/historico", "/api/v1/recompensas"]:
        r = await cliente.get(caminho)
        assert r.status_code == 401, caminho


async def _desbloquear_um_premio(cliente, sessao, admin, familia_id, usuario_id, *,
                                  premio="Uma sobremesa", pontos_necessarios=100, pontos=150):
    """Cria uma trilha com um nível, credita pontos e avalia — deixa um
    prêmio desbloqueado pronto para os testes de premios/solicitar/entregar."""
    from datetime import UTC, datetime
    from uuid import UUID

    from app.models.enums import Frequencia, OrigemPontos, TipoObjetivo
    from app.models.objetivos import Objetivo
    from app.services import pontos as servico_pontos

    familia_id, usuario_id = UUID(familia_id), UUID(usuario_id)

    t = await cliente.post(
        "/api/v1/recompensas/trilhas", headers=_auth(admin),
        json={"nome": "Inglês", "escopo": "all", "beneficiario_id": str(usuario_id)},
    )
    assert t.status_code == 201, t.text
    trilha_id = t.json()["trilha_id"]
    n = await cliente.post(
        f"/api/v1/recompensas/trilhas/{trilha_id}/niveis", headers=_auth(admin),
        json={"pontos_necessarios": pontos_necessarios, "premio": premio},
    )
    assert n.status_code == 201, n.text

    objetivo = Objetivo(
        familia_id=familia_id, titular_id=usuario_id, criador_id=usuario_id,
        tipo=TipoObjetivo.ESTUDO, nome="Curso", meta_periodo=40,
        frequencia=Frequencia.DIARIA,
    )
    sessao.add(objetivo)
    await sessao.flush()
    await servico_pontos.creditar(
        sessao, beneficiario_id=usuario_id, familia_id=familia_id, objetivo=objetivo,
        pontos=pontos, origem=OrigemPontos.SESSAO_ESTUDO,
        chave_idempotencia=f"teste:{objetivo.id}", agora=datetime.now(UTC),
    )
    await sessao.commit()
    return trilha_id


async def test_premios_trazem_o_texto_do_premio_e_a_trilha(cliente, sessao):
    cad = await cliente.post("/api/v1/auth/cadastrar", json=RESPONSAVEL)
    admin = cad.json()["access_token"]
    eu = cad.json()["usuario"]
    familia_id = cad.json()["familia_id"]

    await _desbloquear_um_premio(cliente, sessao, admin, familia_id, eu["id"])
    # /recompensas desbloqueia ao consultar (docstring do endpoint)
    avaliado = await cliente.get("/api/v1/recompensas", headers=_auth(admin))
    assert avaliado.status_code == 200

    r = await cliente.get("/api/v1/recompensas/premios", headers=_auth(admin))
    assert r.status_code == 200
    corpo = r.json()
    assert len(corpo) == 1
    assert corpo[0]["premio"] == "Uma sobremesa"
    assert corpo[0]["trilha_nome"] == "Inglês"
    assert corpo[0]["pontos_necessarios"] == 100
    assert corpo[0]["beneficiario_id"] == eu["id"]
    assert corpo[0]["status"] == "unlocked"


async def test_responsavel_ve_premios_do_dependente(cliente, sessao):
    cad = await cliente.post("/api/v1/auth/cadastrar", json=RESPONSAVEL)
    admin = cad.json()["access_token"]
    familia_id = cad.json()["familia_id"]
    dep = await _dependente(cliente, admin)
    eu_dep = (await cliente.get("/api/v1/auth/eu", headers=_auth(dep))).json()

    await _desbloquear_um_premio(cliente, sessao, admin, familia_id, eu_dep["id"])
    await cliente.get(f"/api/v1/recompensas?beneficiario_id={eu_dep['id']}", headers=_auth(admin))

    r = await cliente.get(
        f"/api/v1/recompensas/premios?beneficiario_id={eu_dep['id']}", headers=_auth(admin)
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["beneficiario_id"] == eu_dep["id"]


async def test_dependente_nao_ve_premios_alheios(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)
    eu_admin = (await cliente.get("/api/v1/auth/eu", headers=_auth(admin))).json()

    r = await cliente.get(
        f"/api/v1/recompensas/premios?beneficiario_id={eu_admin['id']}", headers=_auth(dep)
    )
    assert r.status_code == 403
