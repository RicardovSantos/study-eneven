"""Senhas e tokens.

Duas decisões que a especificação exige e que valem explicar:

- **Argon2 e não bcrypt.** Argon2id é resistente a ataque com GPU por
  consumir memória, não só CPU. É o padrão recomendado hoje.
- **Access token JWT curto + refresh token opaco.** O JWT vale 15 minutos
  e não pode ser revogado — por isso é curto. O refresh é opaco (não
  carrega informação), fica no banco só como hash e pode ser revogado a
  qualquer momento, por dispositivo.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_hasher = PasswordHash.recommended()

TipoToken = Literal["access", "refresh"]


def gerar_hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def conferir_senha(senha: str, hash_guardado: str) -> bool:
    """Compara em tempo constante; nunca levanta exceção para hash inválido."""
    try:
        return _hasher.verify(senha, hash_guardado)
    except Exception:
        return False


def criar_access_token(usuario_id: UUID, familia_id: UUID | None, papel: str | None) -> str:
    """JWT de vida curta.

    O papel vai no token só para a interface saber o que exibir. O
    backend NUNCA confia nele para autorizar: toda decisão consulta
    `family_members` no banco (seção 7.3).
    """
    s = get_settings()
    agora = datetime.now(UTC)
    corpo: dict[str, Any] = {
        "sub": str(usuario_id),
        "fam": str(familia_id) if familia_id else None,
        "papel": papel,
        "tipo": "access",
        "iat": agora,
        "exp": agora + timedelta(minutes=s.ACCESS_TOKEN_MINUTES),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(corpo, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def ler_access_token(token: str) -> dict[str, Any] | None:
    """Devolve o conteúdo, ou None se inválido/expirado/adulterado."""
    s = get_settings()
    try:
        corpo = jwt.decode(
            token,
            s.JWT_SECRET_KEY,
            algorithms=[s.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "tipo"]},
        )
    except jwt.PyJWTError:
        return None
    # Um refresh token não pode ser usado como access token.
    if corpo.get("tipo") != "access":
        return None
    return corpo


def gerar_refresh_token() -> tuple[str, str]:
    """Devolve (token em claro, hash para guardar).

    O claro vai para o cliente uma única vez. O banco guarda só o hash:
    quem vazar a tabela não consegue se passar por ninguém.

    SHA-256 basta aqui — diferente de senha, este valor é aleatório de
    256 bits, então não há o que adivinhar por força bruta.
    """
    claro = secrets.token_urlsafe(48)
    return claro, hashlib.sha256(claro.encode()).hexdigest()


def hash_refresh_token(claro: str) -> str:
    return hashlib.sha256(claro.encode()).hexdigest()
