"""Testes dos endpoints HTTP — o contrato que o front-end vai consumir."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import Sessao as _  # noqa: F401
from app.db.session import get_sessao
from app.main import app

CADASTRO = {
    "nome_exibicao": "Ricardo Vieira dos Santos",
    "username": "ricardo",
    "email": "ricardo@exemplo.com",
    "senha": "senha1234",
    "nome_familia": "Família Santos",
}


@pytest_asyncio.fixture
async def cliente(sessao):
    """Cliente HTTP com o banco de teste no lugar do real."""
    async def _sessao_de_teste():
        yield sessao

    app.dependency_overrides[get_sessao] = _sessao_de_teste
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def test_cadastro_devolve_201_e_sessao(cliente):
    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["papel"] == "admin"
    assert corpo["usuario"]["username"] == "ricardo"


async def test_resposta_nunca_devolve_o_hash_da_senha(cliente):
    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    texto = r.text
    assert "senha_hash" not in texto
    assert "argon2" not in texto
    assert CADASTRO["senha"] not in texto


async def test_refresh_vai_em_cookie_httponly_e_nao_no_corpo(cliente):
    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    assert "devlog_refresh" not in r.text

    bruto = r.headers.get("set-cookie", "")
    assert "devlog_refresh=" in bruto
    assert "HttpOnly" in bruto


@pytest.mark.parametrize(
    "campo,valor",
    [("senha", "1234567"), ("senha", "12345678"), ("username", "ab"),
     ("email", "nao-e-email"), ("nome_exibicao", "R")],
)
async def test_cadastro_recusa_dados_invalidos(cliente, campo, valor):
    r = await cliente.post("/api/v1/auth/cadastrar", json={**CADASTRO, campo: valor})
    assert r.status_code == 422


async def test_cadastro_repetido_devolve_409(cliente):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    assert r.status_code == 409


async def test_login_e_rota_protegida(cliente):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    r = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "ricardo", "senha": "senha1234"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    eu = await cliente.get("/api/v1/auth/eu", headers={"Authorization": f"Bearer {token}"})
    assert eu.status_code == 200
    assert eu.json()["username"] == "ricardo"


async def test_senha_errada_devolve_401(cliente):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    r = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "ricardo", "senha": "errada12"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize(
    "cabecalho",
    [None, {"Authorization": "Bearer invalido"}, {"Authorization": "Basic abc"},
     {"Authorization": "Bearer "}],
)
async def test_rota_protegida_sem_token_valido_devolve_401(cliente, cabecalho):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    r = await cliente.get("/api/v1/auth/eu", headers=cabecalho or {})
    assert r.status_code == 401


async def test_renovar_usa_o_cookie(cliente):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    r = await cliente.post("/api/v1/auth/renovar")
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_sair_invalida_a_sessao(cliente):
    await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    assert (await cliente.post("/api/v1/auth/sair")).status_code == 204
    assert (await cliente.post("/api/v1/auth/renovar")).status_code == 401


async def test_dependente_nao_acessa_rota_de_administrador(cliente):
    """Critério de aceite da Fase 3: o bloqueio vale na API, não só na tela."""
    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    token_admin = r.json()["access_token"]

    novo = await cliente.post(
        "/api/v1/auth/dependentes",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"nome_exibicao": "Pedro", "username": "pedro",
              "senha_temporaria": "temporaria1", "parentesco": "filho"},
    )
    assert novo.status_code == 201

    entrada = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    token_dep = entrada.json()["access_token"]
    assert entrada.json()["papel"] == "dependent"

    proibido = await cliente.post(
        "/api/v1/auth/dependentes",
        headers={"Authorization": f"Bearer {token_dep}"},
        json={"nome_exibicao": "Outro", "username": "outro", "senha_temporaria": "temporaria1"},
    )
    assert proibido.status_code == 403


async def test_papel_forjado_no_token_nao_da_acesso(cliente):
    """O papel do JWT serve só para a interface. A autorização lê o banco."""
    import jwt

    from app.core.config import get_settings

    r = await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)
    admin = r.json()["access_token"]
    await cliente.post(
        "/api/v1/auth/dependentes",
        headers={"Authorization": f"Bearer {admin}"},
        json={"nome_exibicao": "Pedro", "username": "pedro", "senha_temporaria": "temporaria1"},
    )
    entrada = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    corpo_dep = jwt.decode(
        entrada.json()["access_token"], get_settings().JWT_SECRET_KEY, algorithms=["HS256"]
    )

    # o dependente reemite o próprio token dizendo que é admin
    s = get_settings()
    forjado = jwt.encode({**corpo_dep, "papel": "admin"}, s.JWT_SECRET_KEY, algorithm="HS256")

    proibido = await cliente.post(
        "/api/v1/auth/dependentes",
        headers={"Authorization": f"Bearer {forjado}"},
        json={"nome_exibicao": "Invasor", "username": "invasor",
              "senha_temporaria": "temporaria1"},
    )
    assert proibido.status_code == 403


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _admin_e_dependente(cliente):
    admin = (await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)).json()["access_token"]
    novo = await cliente.post(
        "/api/v1/auth/dependentes", headers=_auth(admin),
        json={"nome_exibicao": "Pedro", "username": "pedro", "senha_temporaria": "temporaria1"},
    )
    return admin, novo.json()["id"]


async def test_responsavel_redefine_a_senha_do_dependente(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)

    r = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/redefinir-senha",
        headers=_auth(admin), json={"senha_nova": "novaSenha1"},
    )
    assert r.status_code == 204

    velha = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    assert velha.status_code == 401

    nova = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "novaSenha1"}
    )
    assert nova.status_code == 200


async def test_redefinir_senha_derruba_a_sessao_aberta(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)
    entrada = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    assert entrada.status_code == 200

    await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/redefinir-senha",
        headers=_auth(admin), json={"senha_nova": "novaSenha1"},
    )
    # o cookie de refresh do dependente é o mesmo client (jar compartilhado);
    # renovar precisa falhar porque sair_de_todos revogou o token dele.
    renovar = await cliente.post("/api/v1/auth/renovar")
    assert renovar.status_code == 401


async def test_redefinir_senha_recusa_senha_fraca(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)
    r = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/redefinir-senha",
        headers=_auth(admin), json={"senha_nova": "somenteletras"},
    )
    assert r.status_code == 422


async def test_dependente_nao_redefine_a_propria_senha_por_esta_rota(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)
    entrada = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    token_dep = entrada.json()["access_token"]
    r = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/redefinir-senha",
        headers=_auth(token_dep), json={"senha_nova": "novaSenha1"},
    )
    assert r.status_code == 403


async def test_desativar_e_reativar_dependente(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)

    desativado = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/desativar", headers=_auth(admin)
    )
    assert desativado.status_code == 200
    assert desativado.json()["ativo"] is False

    bloqueado = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    assert bloqueado.status_code == 403

    reativado = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/reativar", headers=_auth(admin)
    )
    assert reativado.status_code == 200
    assert reativado.json()["ativo"] is True

    liberado = await cliente.post(
        "/api/v1/auth/entrar", json={"identificador": "pedro", "senha": "temporaria1"}
    )
    assert liberado.status_code == 200


async def test_desativar_dependente_de_outra_familia_da_404(cliente):
    admin_dono, dep_id = await _admin_e_dependente(cliente)
    outro_admin = (await cliente.post(
        "/api/v1/auth/cadastrar",
        json={**CADASTRO, "username": "outra", "email": "outra@exemplo.com",
              "nome_familia": "Outra"},
    )).json()["access_token"]

    r = await cliente.post(
        f"/api/v1/auth/dependentes/{dep_id}/desativar", headers=_auth(outro_admin)
    )
    assert r.status_code == 404


async def test_admin_nao_desativa_a_propria_conta_por_esta_rota(cliente):
    admin = (await cliente.post("/api/v1/auth/cadastrar", json=CADASTRO)).json()
    r = await cliente.post(
        f"/api/v1/auth/dependentes/{admin['usuario']['id']}/desativar",
        headers=_auth(admin["access_token"]),
    )
    assert r.status_code == 404


async def test_painel_da_familia_mostra_quem_esta_desativado(cliente):
    admin, dep_id = await _admin_e_dependente(cliente)
    await cliente.post(f"/api/v1/auth/dependentes/{dep_id}/desativar", headers=_auth(admin))

    painel = await cliente.get("/api/v1/dashboard/familia", headers=_auth(admin))
    assert painel.status_code == 200
    assert painel.json()["dependentes"][0]["ativo"] is False


async def test_health_live_nao_depende_do_banco(cliente):
    r = await cliente.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "vivo"
