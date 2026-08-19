"""Testes de autenticação contra um banco de verdade."""

import pytest

from app.core.exceptions import (
    ContaDesativada,
    CredenciaisInvalidas,
    JaExiste,
    NaoAutenticado,
    SemPermissao,
)
from app.core.security import ler_access_token
from app.models.enums import PapelFamiliar
from app.repositories import tokens as repo_tokens
from app.repositories import usuarios as repo
from app.services import auth

CADASTRO = dict(
    nome_exibicao="Ricardo Vieira dos Santos",
    username="ricardo",
    email="ricardo@exemplo.com",
    senha="senha1234",
    nome_familia="Família Santos",
)


async def _responsavel(sessao):
    return await auth.cadastrar_responsavel(sessao, **CADASTRO)


# ---------- cadastro ----------

async def test_cadastro_cria_usuario_familia_e_vinculo(sessao):
    aberta = await _responsavel(sessao)
    assert aberta.papel == PapelFamiliar.ADMIN.value
    assert aberta.familia_id is not None

    vinculo = await repo.vinculo_ativo(sessao, aberta.usuario.id)
    assert vinculo.papel == PapelFamiliar.ADMIN


async def test_senha_nunca_e_guardada_em_texto_puro(sessao):
    """O problema mais grave da versão em localStorage."""
    aberta = await _responsavel(sessao)
    guardado = await repo.por_id(sessao, aberta.usuario.id)
    assert guardado.senha_hash != CADASTRO["senha"]
    assert CADASTRO["senha"] not in guardado.senha_hash
    assert guardado.senha_hash.startswith("$argon2id$")


async def test_username_e_email_sao_normalizados(sessao):
    await auth.cadastrar_responsavel(sessao, **{**CADASTRO, "username": "RiCaRdO",
                                                "email": "Ricardo@Exemplo.COM"})
    assert await repo.por_username(sessao, "ricardo") is not None
    assert await repo.por_email(sessao, "ricardo@exemplo.com") is not None


async def test_username_repetido_e_recusado(sessao):
    await _responsavel(sessao)
    with pytest.raises(JaExiste):
        await auth.cadastrar_responsavel(sessao, **{**CADASTRO, "email": "outro@exemplo.com"})


async def test_email_repetido_e_recusado(sessao):
    await _responsavel(sessao)
    with pytest.raises(JaExiste):
        await auth.cadastrar_responsavel(sessao, **{**CADASTRO, "username": "outro"})


# ---------- login ----------

async def test_login_por_username_e_por_email(sessao):
    await _responsavel(sessao)
    for ident in ("ricardo", "ricardo@exemplo.com"):
        aberta = await auth.entrar(sessao, identificador=ident, senha="senha1234")
        assert aberta.usuario.username == "ricardo"


async def test_senha_errada_nao_entra(sessao):
    await _responsavel(sessao)
    with pytest.raises(CredenciaisInvalidas):
        await auth.entrar(sessao, identificador="ricardo", senha="errada12")


async def test_usuario_inexistente_da_o_mesmo_erro_que_senha_errada(sessao):
    """Mensagens diferentes revelariam quais contas existem."""
    await _responsavel(sessao)
    with pytest.raises(CredenciaisInvalidas) as sem_conta:
        await auth.entrar(sessao, identificador="ninguem", senha="senha1234")
    with pytest.raises(CredenciaisInvalidas) as senha_ruim:
        await auth.entrar(sessao, identificador="ricardo", senha="errada12")
    assert sem_conta.value.detail == senha_ruim.value.detail


async def test_conta_desativada_nao_entra(sessao):
    aberta = await _responsavel(sessao)
    aberta.usuario.ativo = False
    await sessao.flush()
    with pytest.raises(ContaDesativada):
        await auth.entrar(sessao, identificador="ricardo", senha="senha1234")


async def test_token_carrega_familia_e_papel(sessao):
    aberta = await _responsavel(sessao)
    corpo = ler_access_token(aberta.access_token)
    assert corpo["sub"] == str(aberta.usuario.id)
    assert corpo["fam"] == str(aberta.familia_id)
    assert corpo["papel"] == "admin"


# ---------- dependentes ----------

async def test_responsavel_cria_dependente(sessao):
    resp = await _responsavel(sessao)
    dep = await auth.criar_dependente(
        sessao, responsavel=resp.usuario, familia_id=resp.familia_id,
        nome_exibicao="Pedro", username="pedro", email=None,
        senha_temporaria="temporaria1", parentesco="filho",
    )
    vinculo = await repo.vinculo_ativo(sessao, dep.id)
    assert vinculo.papel == PapelFamiliar.DEPENDENTE
    assert vinculo.familia_id == resp.familia_id


async def test_dependente_entra_com_a_propria_conta(sessao):
    resp = await _responsavel(sessao)
    await auth.criar_dependente(
        sessao, responsavel=resp.usuario, familia_id=resp.familia_id,
        nome_exibicao="Pedro", username="pedro", email=None, senha_temporaria="temporaria1",
    )
    aberta = await auth.entrar(sessao, identificador="pedro", senha="temporaria1")
    assert aberta.papel == PapelFamiliar.DEPENDENTE.value


async def test_dependente_nao_cria_outro_dependente(sessao):
    """Papel vem do banco: um dependente não escala o próprio acesso."""
    resp = await _responsavel(sessao)
    dep = await auth.criar_dependente(
        sessao, responsavel=resp.usuario, familia_id=resp.familia_id,
        nome_exibicao="Pedro", username="pedro", email=None, senha_temporaria="temporaria1",
    )
    with pytest.raises(SemPermissao):
        await auth.criar_dependente(
            sessao, responsavel=dep, familia_id=resp.familia_id,
            nome_exibicao="Outro", username="outro", email=None, senha_temporaria="temporaria1",
        )


async def test_responsavel_nao_cria_dependente_em_familia_alheia(sessao):
    """Isolamento entre famílias — critério de aceite da Fase 3."""
    a = await _responsavel(sessao)
    b = await auth.cadastrar_responsavel(
        sessao, nome_exibicao="Outra", username="outra", email="outra@exemplo.com",
        senha="senha1234", nome_familia="Família Outra",
    )
    with pytest.raises(SemPermissao):
        await auth.criar_dependente(
            sessao, responsavel=a.usuario, familia_id=b.familia_id,
            nome_exibicao="Invasor", username="invasor", email=None,
            senha_temporaria="temporaria1",
        )


# ---------- refresh token ----------

async def test_refresh_e_guardado_so_como_hash(sessao):
    aberta = await _responsavel(sessao)
    from sqlalchemy import select

    from app.models.identidade import RefreshToken
    r = await sessao.execute(select(RefreshToken))
    guardado = r.scalars().first()
    assert guardado.token_hash != aberta.refresh_claro


async def test_renovar_devolve_par_novo(sessao):
    aberta = await _responsavel(sessao)
    nova = await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)
    assert nova.refresh_claro != aberta.refresh_claro
    assert ler_access_token(nova.access_token) is not None


async def test_refresh_antigo_para_de_valer_apos_rotacao(sessao):
    aberta = await _responsavel(sessao)
    await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)
    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)


async def test_reuso_de_token_derruba_todas_as_sessoes(sessao):
    """Reuso indica cópia roubada: recusar só a chamada deixaria o
    atacante seguir com o token que ele rotacionou."""
    aberta = await _responsavel(sessao)
    nova = await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)

    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)

    # o token legítimo do usuário também caiu
    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro=nova.refresh_claro)


async def test_token_inventado_nao_renova(sessao):
    await _responsavel(sessao)
    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro="token-que-nunca-existiu")


async def test_sair_revoga_o_token(sessao):
    aberta = await _responsavel(sessao)
    await auth.sair(sessao, refresh_claro=aberta.refresh_claro)
    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)


async def test_sair_de_todos_os_aparelhos(sessao):
    aberta = await _responsavel(sessao)
    outra = await auth.entrar(sessao, identificador="ricardo", senha="senha1234")

    quantos = await auth.sair_de_todos(sessao, usuario_id=aberta.usuario.id)
    assert quantos == 2

    for t in (aberta.refresh_claro, outra.refresh_claro):
        with pytest.raises(NaoAutenticado):
            await auth.renovar(sessao, refresh_claro=t)


async def test_token_expirado_nao_renova(sessao):
    from datetime import UTC, datetime, timedelta
    aberta = await _responsavel(sessao)
    from app.core.security import hash_refresh_token
    guardado = await repo_tokens.por_hash(sessao, hash_refresh_token(aberta.refresh_claro))
    guardado.expira_em = datetime.now(UTC) - timedelta(seconds=1)
    await sessao.flush()
    with pytest.raises(NaoAutenticado):
        await auth.renovar(sessao, refresh_claro=aberta.refresh_claro)
