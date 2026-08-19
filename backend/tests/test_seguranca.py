"""Testes de senha e token — o que protege todas as contas."""

from uuid import uuid4

import pytest

from app.core.security import (
    conferir_senha, criar_access_token, gerar_hash_senha,
    gerar_refresh_token, hash_refresh_token, ler_access_token,
)


def test_hash_nao_guarda_a_senha():
    senha = "senha-do-ricardo"
    h = gerar_hash_senha(senha)
    assert senha not in h
    assert h.startswith("$argon2id$")


def test_mesma_senha_gera_hashes_diferentes():
    """Salt aleatório: dois usuários com a mesma senha não se denunciam."""
    assert gerar_hash_senha("igual") != gerar_hash_senha("igual")


@pytest.mark.parametrize("errada", ["", "outra", "senha-do-ricard", "SENHA-DO-RICARDO"])
def test_senha_errada_nao_passa(errada):
    assert conferir_senha(errada, gerar_hash_senha("senha-do-ricardo")) is False


def test_hash_invalido_nao_explode():
    """Um hash corrompido no banco deve negar o acesso, não derrubar a API."""
    assert conferir_senha("qualquer", "isso-nao-e-um-hash") is False


def test_token_carrega_o_usuario():
    u, f = uuid4(), uuid4()
    corpo = ler_access_token(criar_access_token(u, f, "admin"))
    assert corpo is not None
    assert corpo["sub"] == str(u)
    assert corpo["fam"] == str(f)
    assert corpo["papel"] == "admin"


def test_token_adulterado_e_recusado():
    t = criar_access_token(uuid4(), uuid4(), "dependent")
    assert ler_access_token(t[:-4] + "aaaa") is None


def test_token_de_outra_chave_e_recusado():
    import jwt
    forjado = jwt.encode(
        {"sub": str(uuid4()), "tipo": "access", "exp": 9999999999},
        "chave-do-atacante", algorithm="HS256",
    )
    assert ler_access_token(forjado) is None


def test_token_sem_expiracao_e_recusado():
    """Sem exp, um token roubado valeria para sempre."""
    import jwt
    from app.core.config import get_settings
    s = get_settings()
    sem_exp = jwt.encode(
        {"sub": str(uuid4()), "tipo": "access"}, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM
    )
    assert ler_access_token(sem_exp) is None


def test_refresh_nao_pode_ser_usado_como_access():
    """Tipos separados evitam que o token de vida longa vire acesso direto."""
    import jwt
    from app.core.config import get_settings
    s = get_settings()
    t = jwt.encode(
        {"sub": str(uuid4()), "tipo": "refresh", "exp": 9999999999},
        s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM,
    )
    assert ler_access_token(t) is None


def test_refresh_token_e_guardado_como_hash():
    claro, guardado = gerar_refresh_token()
    assert claro != guardado
    assert len(guardado) == 64
    assert hash_refresh_token(claro) == guardado


def test_refresh_tokens_nao_se_repetem():
    assert len({gerar_refresh_token()[0] for _ in range(200)}) == 200
