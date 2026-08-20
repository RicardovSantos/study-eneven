"""Testes HTTP de matérias."""

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
        json={"nome_exibicao": "Pedro", "username": "pedro", "senha_temporaria": "temporaria1"},
    )
    r = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    return r.json()["access_token"]


async def test_criar_e_listar_materia(cliente):
    admin = await _admin(cliente)
    r = await cliente.post(
        "/api/v1/materias", headers=_auth(admin),
        json={"nome": "Inglês", "cor": "#5B4FE8"},
    )
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["nome"] == "Inglês"
    assert corpo["ativo"] is True

    lista = await cliente.get("/api/v1/materias", headers=_auth(admin))
    assert lista.status_code == 200
    assert [m["nome"] for m in lista.json()] == ["Inglês"]


async def test_dependente_ve_a_lista_mas_nao_cria(cliente):
    admin = await _admin(cliente)
    dep = await _dependente(cliente, admin)
    await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Inglês"})

    ok = await cliente.get("/api/v1/materias", headers=_auth(dep))
    assert ok.status_code == 200
    assert len(ok.json()) == 1

    proibido = await cliente.post(
        "/api/v1/materias", headers=_auth(dep), json={"nome": "Matemática"}
    )
    assert proibido.status_code == 403


async def test_nome_duplicado_e_recusado(cliente):
    admin = await _admin(cliente)
    await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Inglês"})
    r = await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Inglês"})
    assert r.status_code == 409


async def test_editar_materia(cliente):
    admin = await _admin(cliente)
    m = await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Ingles"})
    materia_id = m.json()["id"]

    r = await cliente.patch(
        f"/api/v1/materias/{materia_id}", headers=_auth(admin), json={"nome": "Inglês"}
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Inglês"


async def test_arquivar_materia_some_da_lista_padrao(cliente):
    admin = await _admin(cliente)
    m = await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Inglês"})
    materia_id = m.json()["id"]

    r = await cliente.delete(f"/api/v1/materias/{materia_id}", headers=_auth(admin))
    assert r.status_code == 204

    lista = await cliente.get("/api/v1/materias", headers=_auth(admin))
    assert lista.json() == []

    com_inativas = await cliente.get(
        "/api/v1/materias?incluir_inativas=true", headers=_auth(admin)
    )
    assert len(com_inativas.json()) == 1
    assert com_inativas.json()[0]["ativo"] is False


async def test_objetivo_com_materia_de_outra_familia_da_404(cliente):
    admin_a = await _admin(cliente)
    m = await cliente.post("/api/v1/materias", headers=_auth(admin_a), json={"nome": "Inglês"})
    materia_id = m.json()["id"]

    admin_b = (await cliente.post(
        "/api/v1/auth/cadastrar",
        json={**RESPONSAVEL, "username": "outro", "email": "outro@exemplo.com",
              "nome_familia": "Outra"},
    )).json()["access_token"]

    r = await cliente.post(
        "/api/v1/objetivos", headers=_auth(admin_b),
        json={"tipo": "study", "nome": "Curso", "meta_periodo": 40, "frequencia": "daily",
              "materia_id": materia_id},
    )
    assert r.status_code == 404


async def test_objetivo_com_materia_da_propria_familia_funciona(cliente):
    admin = await _admin(cliente)
    m = await cliente.post("/api/v1/materias", headers=_auth(admin), json={"nome": "Inglês"})
    materia_id = m.json()["id"]

    r = await cliente.post(
        "/api/v1/objetivos", headers=_auth(admin),
        json={"tipo": "study", "nome": "Curso", "meta_periodo": 40, "frequencia": "daily",
              "materia_id": materia_id},
    )
    assert r.status_code == 201
    assert r.json()["materia_id"] == materia_id


async def test_rotas_de_materias_exigem_autenticacao(cliente):
    r = await cliente.get("/api/v1/materias")
    assert r.status_code == 401
