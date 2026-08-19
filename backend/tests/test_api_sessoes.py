"""Testes HTTP das sessões — inclusive as tentativas de burlar o tempo."""

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
OBJETIVO = {"tipo": "study", "nome": "Curso de Inglês", "meta_periodo": 40,
            "frequencia": "daily"}


@pytest_asyncio.fixture
async def cliente(sessao):
    async def _sessao_de_teste():
        yield sessao

    app.dependency_overrides[get_sessao] = _sessao_de_teste
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as c:
        yield c
    app.dependency_overrides.clear()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _preparar(cliente, objetivo=None):
    r = await cliente.post("/api/v1/auth/cadastrar", json=RESPONSAVEL)
    token = r.json()["access_token"]
    obj = await cliente.post(
        "/api/v1/objetivos", headers=_auth(token), json=objetivo or OBJETIVO
    )
    ocs = (await cliente.get("/api/v1/ocorrencias", headers=_auth(token))).json()
    return token, obj.json(), ocs[0]


async def test_abrir_e_consultar_a_sessao_aberta(cliente):
    """O estado vive no servidor: fechar o navegador não perde a sessão."""
    token, obj, oc = await _preparar(cliente)

    r = await cliente.post(
        "/api/v1/sessoes", headers=_auth(token),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]},
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "active"

    aberta = await cliente.get("/api/v1/sessoes/aberta", headers=_auth(token))
    assert aberta.json()["id"] == r.json()["id"]


async def test_sem_sessao_aberta_devolve_nulo(cliente):
    token, _, _ = await _preparar(cliente)
    r = await cliente.get("/api/v1/sessoes/aberta", headers=_auth(token))
    assert r.json() is None


async def test_cliente_nao_consegue_declarar_tempo(cliente):
    """A tentativa mais óbvia de fraude: mandar o tempo no corpo.

    O contrato do heartbeat não tem campo de tempo. Mesmo enviando um,
    ele é ignorado — quem mede é o servidor.
    """
    token, obj, oc = await _preparar(cliente)
    se = (await cliente.post(
        "/api/v1/sessoes", headers=_auth(token),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]},
    )).json()

    r = await cliente.post(
        f"/api/v1/sessoes/{se['id']}/heartbeat",
        headers=_auth(token),
        json={"capturando": False, "segundos": 99999, "segundos_validos": 99999},
    )
    assert r.status_code == 200
    # o tempo real decorrido no teste é de milissegundos
    assert r.json()["sessao"]["segundos_validos"] < 5


async def test_sessao_verificada_pela_web_e_recusada_quando_exigida(cliente):
    """A web não monitora outros apps; não pode fingir que monitora."""
    token, obj, oc = await _preparar(
        cliente, {**OBJETIVO, "exige_sessao_verificada": True}
    )
    r = await cliente.post(
        "/api/v1/sessoes", headers=_auth(token),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"], "verificada": False},
    )
    assert r.status_code == 403
    assert "Android" in r.json()["detail"]


async def test_pausar_e_retomar(cliente):
    token, obj, oc = await _preparar(cliente)
    se = (await cliente.post(
        "/api/v1/sessoes", headers=_auth(token),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]},
    )).json()

    p = await cliente.post(f"/api/v1/sessoes/{se['id']}/pausar", headers=_auth(token))
    assert p.json()["estado"] == "paused"

    v = await cliente.post(f"/api/v1/sessoes/{se['id']}/retomar", headers=_auth(token))
    assert v.json()["estado"] == "active"


async def test_finalizar_encerra_e_responde_o_apurado(cliente):
    token, obj, oc = await _preparar(cliente)
    se = (await cliente.post(
        "/api/v1/sessoes", headers=_auth(token),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]},
    )).json()

    r = await cliente.post(
        f"/api/v1/sessoes/{se['id']}/finalizar",
        headers=_auth(token), json={"resumo": "Revisei os verbos irregulares."},
    )
    assert r.status_code == 200
    assert r.json()["sessao"]["estado"] == "finished"
    assert r.json()["minutos_validos"] == 0      # duração real do teste


async def test_segunda_sessao_simultanea_e_recusada(cliente):
    token, obj, oc = await _preparar(cliente)
    corpo = {"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]}
    await cliente.post("/api/v1/sessoes", headers=_auth(token), json=corpo)
    r = await cliente.post("/api/v1/sessoes", headers=_auth(token), json=corpo)
    assert r.status_code == 403


async def test_sessao_de_outra_familia_da_404(cliente):
    token_a, obj, oc = await _preparar(cliente)
    se = (await cliente.post(
        "/api/v1/sessoes", headers=_auth(token_a),
        json={"objetivo_id": obj["id"], "ocorrencia_id": oc["id"]},
    )).json()

    outra = await cliente.post(
        "/api/v1/auth/cadastrar",
        json={**RESPONSAVEL, "username": "outra", "email": "outra@exemplo.com",
              "nome_familia": "Outra"},
    )
    token_b = outra.json()["access_token"]

    r = await cliente.get(f"/api/v1/sessoes/{se['id']}", headers=_auth(token_b))
    assert r.status_code == 404


async def test_rotas_de_sessao_exigem_autenticacao(cliente):
    for metodo, caminho in [
        ("post", "/api/v1/sessoes"), ("get", "/api/v1/sessoes/aberta")
    ]:
        corpo = {"json": {"objetivo_id": "00000000-0000-0000-0000-000000000000"}} \
            if metodo == "post" else {}
        r = await getattr(cliente, metodo)(caminho, **corpo)
        assert r.status_code == 401, caminho
