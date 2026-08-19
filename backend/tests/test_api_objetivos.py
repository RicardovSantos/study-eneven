"""Testes HTTP de objetivos e ocorrências, com foco em autorização."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_sessao
from app.main import app

RESPONSAVEL = {
    "nome_exibicao": "Ricardo Vieira dos Santos",
    "username": "ricardo",
    "email": "ricardo@exemplo.com",
    "senha": "senha1234",
    "nome_familia": "Família Santos",
}
OBJETIVO = {
    "tipo": "study",
    "nome": "Curso de Inglês",
    "meta_periodo": 40,
    "frequencia": "daily",
    "permite_adiantar": True,
    "max_adiantamentos": 1,
}


@pytest_asyncio.fixture
async def cliente(sessao):
    async def _sessao_de_teste():
        yield sessao

    app.dependency_overrides[get_sessao] = _sessao_de_teste
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as c:
        yield c
    app.dependency_overrides.clear()


async def _entrar_admin(cliente) -> str:
    r = await cliente.post("/api/v1/auth/cadastrar", json=RESPONSAVEL)
    return r.json()["access_token"]


async def _criar_dependente(cliente, token_admin) -> str:
    await cliente.post(
        "/api/v1/auth/dependentes",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"nome_exibicao": "Pedro", "username": "pedro", "senha_temporaria": "temporaria1"},
    )
    r = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_criar_objetivo_ja_materializa_a_agenda(cliente):
    """Sem ocorrências, o objetivo não apareceria na tela Estudar."""
    token = await _entrar_admin(cliente)
    r = await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)
    assert r.status_code == 201

    ocs = await cliente.get("/api/v1/ocorrencias", headers=_auth(token))
    assert ocs.status_code == 200
    assert len(ocs.json()) >= 1


async def test_tarefa_sem_pontos_fixos_e_recusada(cliente):
    token = await _entrar_admin(cliente)
    r = await cliente.post(
        "/api/v1/objetivos", headers=_auth(token),
        json={**OBJETIVO, "tipo": "task", "frequencia": "monthly"},
    )
    assert r.status_code == 422


async def test_dependente_nao_cadastra_objetivo(cliente):
    """Quem decide o que o dependente estuda é o responsável."""
    admin = await _entrar_admin(cliente)
    dep = await _criar_dependente(cliente, admin)
    r = await cliente.post("/api/v1/objetivos", headers=_auth(dep), json=OBJETIVO)
    assert r.status_code == 403


async def test_dependente_ve_so_os_proprios_objetivos(cliente):
    admin = await _entrar_admin(cliente)
    dep = await _criar_dependente(cliente, admin)

    # um objetivo do responsável
    await cliente.post("/api/v1/objetivos", headers=_auth(admin), json=OBJETIVO)

    lista = await cliente.get("/api/v1/objetivos", headers=_auth(dep))
    assert lista.json() == []


async def test_responsavel_cadastra_para_o_dependente(cliente):
    admin = await _entrar_admin(cliente)
    dep = await _criar_dependente(cliente, admin)
    eu_dep = await cliente.get("/api/v1/auth/eu", headers=_auth(dep))
    id_dep = eu_dep.json()["id"]

    r = await cliente.post(
        "/api/v1/objetivos", headers=_auth(admin), json={**OBJETIVO, "titular_id": id_dep}
    )
    assert r.status_code == 201
    assert r.json()["titular_id"] == id_dep

    # agora o dependente enxerga
    lista = await cliente.get("/api/v1/objetivos", headers=_auth(dep))
    assert len(lista.json()) == 1


async def test_objetivo_de_outra_familia_da_404(cliente):
    """404 e não 403: um 403 confirmaria que aquele id existe."""
    admin_a = await _entrar_admin(cliente)
    r = await cliente.post("/api/v1/objetivos", headers=_auth(admin_a), json=OBJETIVO)
    id_a = r.json()["id"]

    outra = await cliente.post(
        "/api/v1/auth/cadastrar",
        json={**RESPONSAVEL, "username": "outra", "email": "outra@exemplo.com",
              "nome_familia": "Outra Família"},
    )
    token_b = outra.json()["access_token"]

    achou = await cliente.get(f"/api/v1/objetivos/{id_a}", headers=_auth(token_b))
    assert achou.status_code == 404


async def test_dependente_nao_edita_objetivo(cliente):
    admin = await _entrar_admin(cliente)
    dep = await _criar_dependente(cliente, admin)
    eu_dep = await cliente.get("/api/v1/auth/eu", headers=_auth(dep))

    r = await cliente.post(
        "/api/v1/objetivos", headers=_auth(admin),
        json={**OBJETIVO, "titular_id": eu_dep.json()["id"]},
    )
    id_obj = r.json()["id"]

    editado = await cliente.patch(
        f"/api/v1/objetivos/{id_obj}", headers=_auth(dep), json={"meta_periodo": 5}
    )
    assert editado.status_code == 403


async def test_concluir_credita_pontos_e_devolve_o_momento(cliente):
    token = await _entrar_admin(cliente)
    await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)

    ocs = (await cliente.get("/api/v1/ocorrencias", headers=_auth(token))).json()
    hoje = ocs[0]

    r = await cliente.post(
        f"/api/v1/ocorrencias/{hoje['id']}/concluir",
        headers=_auth(token), json={"minutos_validos": 40},
    )
    assert r.status_code == 200
    assert r.json()["pontos_creditados"] == 40
    assert r.json()["momento"] == "on_time"


async def test_verificado_maior_que_valido_e_recusado(cliente):
    token = await _entrar_admin(cliente)
    await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)
    ocs = (await cliente.get("/api/v1/ocorrencias", headers=_auth(token))).json()

    r = await cliente.post(
        f"/api/v1/ocorrencias/{ocs[0]['id']}/concluir",
        headers=_auth(token), json={"minutos_validos": 10, "minutos_verificados": 40},
    )
    assert r.status_code == 422


async def test_fluxo_de_adiantamento_pela_api(cliente):
    """O fluxo que a tela vai usar: concluir, perguntar a próxima, adiantar."""
    token = await _entrar_admin(cliente)
    await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)
    ocs = (await cliente.get("/api/v1/ocorrencias", headers=_auth(token))).json()
    hoje, amanha = ocs[0], ocs[1]

    # antes de concluir hoje, a próxima não pode ser adiantada
    antes = await cliente.get(
        f"/api/v1/ocorrencias/{hoje['id']}/proxima", headers=_auth(token)
    )
    assert antes.json()["pode_adiantar"] is False
    assert "Conclua a atividade de hoje" in antes.json()["motivo"]

    await cliente.post(
        f"/api/v1/ocorrencias/{hoje['id']}/concluir",
        headers=_auth(token), json={"minutos_validos": 40},
    )

    depois = await cliente.get(
        f"/api/v1/ocorrencias/{hoje['id']}/proxima", headers=_auth(token)
    )
    assert depois.json()["pode_adiantar"] is True
    assert depois.json()["ocorrencia"]["id"] == amanha["id"]

    adiantada = await cliente.post(
        f"/api/v1/ocorrencias/{amanha['id']}/concluir",
        headers=_auth(token), json={"minutos_validos": 40},
    )
    assert adiantada.json()["momento"] == "early"
    assert adiantada.json()["ocorrencia"]["dias_adiantados"] == 1
    # a data prevista continua sendo a de amanhã
    assert adiantada.json()["ocorrencia"]["prevista_para"] == amanha["prevista_para"]


async def test_objetivo_com_historico_e_arquivado_e_nao_excluido(cliente):
    """Excluir levaria junto o histórico que justifica os pontos."""
    token = await _entrar_admin(cliente)
    criado = await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)
    id_obj = criado.json()["id"]

    ocs = (await cliente.get("/api/v1/ocorrencias", headers=_auth(token))).json()
    await cliente.post(
        f"/api/v1/ocorrencias/{ocs[0]['id']}/concluir",
        headers=_auth(token), json={"minutos_validos": 40},
    )

    r = await cliente.delete(f"/api/v1/objetivos/{id_obj}", headers=_auth(token))
    assert r.json()["excluido"] is False

    ainda = await cliente.get(
        f"/api/v1/objetivos/{id_obj}", headers=_auth(token)
    )
    assert ainda.json()["status"] == "archived"


async def test_objetivo_sem_historico_e_excluido_de_fato(cliente):
    token = await _entrar_admin(cliente)
    criado = await cliente.post("/api/v1/objetivos", headers=_auth(token), json=OBJETIVO)
    r = await cliente.delete(f"/api/v1/objetivos/{criado.json()['id']}", headers=_auth(token))
    assert r.json()["excluido"] is True


async def test_sem_token_nenhuma_rota_de_objetivo_responde(cliente):
    for metodo, caminho in [("get", "/api/v1/objetivos"), ("post", "/api/v1/objetivos"),
                            ("get", "/api/v1/ocorrencias")]:
        corpo = {"json": OBJETIVO} if metodo == "post" else {}
        r = await getattr(cliente, metodo)(caminho, **corpo)
        assert r.status_code == 401, caminho
